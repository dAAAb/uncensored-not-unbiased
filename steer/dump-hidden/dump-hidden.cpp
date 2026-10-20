// llama-dump-hidden: write the residual stream (output of every layer) for a list of chat prompts.
//
// Each non-empty line of --positive-file is one user message (escapes such as \n are processed). The message is
// formatted with the model's own chat template exactly as llama-server does (jinja, generation prompt, thinking off),
// evaluated once, and for every layer the output row of the last prompt token and the mean over all prompt tokens are
// written to -o as float32.
//
// Output layout: int32 n_prompts, n_layers, n_embd; then per prompt: last[n_layers][n_embd], mean[n_layers][n_embd].
// Layers whose output is not available for all tokens (the final layer, which llama.cpp computes only for the output
// row) are written as zeros.
//
// Build: copy this folder to llama.cpp/tools/dump-hidden, add `add_subdirectory(dump-hidden)` to tools/CMakeLists.txt,
// then `cmake --build build --target llama-dump-hidden`.

#include "arg.h"
#include "chat.h"
#include "common.h"
#include "ggml-backend.h"
#include "ggml.h"
#include "llama.h"

#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

struct cb_state {
    int                n_layers = 0;
    int                n_embd   = 0;
    int                n_tokens = 0;
    std::vector<float> last;  // [n_layers * n_embd]
    std::vector<float> mean;  // [n_layers * n_embd]
    std::vector<float> tmp;
    int                n_seen = 0;
};

static bool cb_eval(struct ggml_tensor * t, bool ask, void * user_data) {
    auto *     s        = (cb_state *) user_data;
    const bool is_l_out = strncmp(t->name, "l_out-", 6) == 0;
    if (ask) {
        return is_l_out;
    }
    if (!is_l_out || t->type != GGML_TYPE_F32 || t->ne[0] != s->n_embd || t->ne[1] != s->n_tokens ||
        !ggml_is_contiguous(t)) {
        return true;
    }
    const int il = atoi(t->name + 6);
    if (il < 0 || il >= s->n_layers) {
        return true;
    }
    const size_t n = (size_t) s->n_embd * s->n_tokens;
    s->tmp.resize(n);
    ggml_backend_tensor_get(t, s->tmp.data(), 0, n * sizeof(float));
    float * last = s->last.data() + (size_t) il * s->n_embd;
    float * mean = s->mean.data() + (size_t) il * s->n_embd;
    for (int i = 0; i < s->n_embd; i++) {
        last[i]    = s->tmp[(size_t) (s->n_tokens - 1) * s->n_embd + i];
        double acc = 0.0;
        for (int r = 0; r < s->n_tokens; r++) {
            acc += s->tmp[(size_t) r * s->n_embd + i];
        }
        mean[i] = (float) (acc / s->n_tokens);
    }
    s->n_seen++;
    return true;
}

static void print_usage(int, char ** argv) {
    printf("usage: %s -m model.gguf --positive-file prompts.txt -o hidden.bin [-ngl N] [-t N]\n", argv[0]);
}

int main(int argc, char ** argv) {
    std::setlocale(LC_NUMERIC, "C");

    common_params params;
    params.out_file = "hidden.bin";
    common_init();
    if (!common_params_parse(argc, argv, params, LLAMA_EXAMPLE_CVECTOR_GENERATOR, print_usage)) {
        return 1;
    }

    cb_state st;
    params.cb_eval           = cb_eval;
    params.cb_eval_user_data = &st;
    params.warmup            = false;

    llama_backend_init();
    llama_numa_init(params.numa);
    auto   llama_init = common_init_from_params(params);
    auto * model      = llama_init->model();
    auto * ctx        = llama_init->context();
    if (model == nullptr || ctx == nullptr) {
        fprintf(stderr, "failed to load model\n");
        return 1;
    }

    st.n_layers = llama_model_n_layer(model);
    st.n_embd   = llama_model_n_embd(model);

    std::vector<std::string> msgs;
    {
        std::ifstream in(params.cvector_positive_file);
        if (!in.is_open()) {
            fprintf(stderr, "cannot open %s\n", params.cvector_positive_file.c_str());
            return 1;
        }
        std::string line;
        while (std::getline(in, line)) {
            if (line.empty()) {
                continue;
            }
            string_process_escapes(line);
            msgs.push_back(line);
        }
    }

    auto                tmpls = common_chat_templates_init(model, params.chat_template);
    const llama_vocab * vocab = llama_model_get_vocab(model);

    FILE * fo = fopen(params.out_file.c_str(), "wb");
    if (!fo) {
        fprintf(stderr, "cannot write %s\n", params.out_file.c_str());
        return 1;
    }
    const int32_t hdr[3] = { (int32_t) msgs.size(), st.n_layers, st.n_embd };
    fwrite(hdr, sizeof(hdr), 1, fo);

    for (size_t i = 0; i < msgs.size(); i++) {
        common_chat_templates_inputs inputs;
        common_chat_msg              m;
        m.role                                    = "user";
        m.content                                 = msgs[i];
        inputs.messages                           = { m };
        inputs.add_generation_prompt              = true;
        inputs.use_jinja                          = true;
        inputs.enable_thinking                    = false;
        inputs.chat_template_kwargs["enable_thinking"] = "false";
        const std::string prompt = common_chat_templates_apply(tmpls.get(), inputs).prompt.str();
        if (i == 0) {
            fprintf(stderr, "first formatted prompt:\n---\n%s\n---\n", prompt.c_str());
        }

        std::vector<llama_token> toks = common_tokenize(ctx, prompt, llama_vocab_get_add_bos(vocab), true);
        st.n_tokens                   = (int) toks.size();
        st.n_seen                     = 0;
        st.last.assign((size_t) st.n_layers * st.n_embd, 0.0f);
        st.mean.assign((size_t) st.n_layers * st.n_embd, 0.0f);

        llama_memory_clear(llama_get_memory(ctx), true);
        common_batch batch = common_batch_get_one(ctx, toks);
        if (llama_process(ctx, LLAMA_PROCESS_TYPE_DECODE, batch.get())) {
            fprintf(stderr, "eval failed on prompt %zu\n", i);
            return 1;
        }
        fwrite(st.last.data(), sizeof(float), st.last.size(), fo);
        fwrite(st.mean.data(), sizeof(float), st.mean.size(), fo);
        fflush(fo);
        fprintf(stderr, "[%zu/%zu] %d tokens, %d layers captured\n", i + 1, msgs.size(), st.n_tokens, st.n_seen);
    }
    fclose(fo);
    llama_backend_free();
    return 0;
}
