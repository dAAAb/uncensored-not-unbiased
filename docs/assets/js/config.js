/* Site configuration: the only place to change links, the arXiv entry and the teaser video. */
window.UNU_CONFIG = {
  siteUrl: "https://daaab.github.io/uncensored-not-unbiased/",

  /* arXiv: leave id empty until the preprint is out ("coming soon" is shown and the button is disabled).
     Example: id: "2611.01234" -> https://arxiv.org/abs/2611.01234, and the BibTeX gains eprint fields. */
  arxiv: { id: "" },

  links: {
    paper: "https://github.com/dAAAb/uncensored-not-unbiased/blob/main/paper/main.pdf",
    paperZh: "https://github.com/dAAAb/uncensored-not-unbiased/blob/main/paper/main_zh.pdf",
    code: "https://github.com/dAAAb/uncensored-not-unbiased",
    blog: { zh: "https://blog.juchunko.com/zh/uncensored-not-unbiased/", en: "https://blog.juchunko.com/en/uncensored-not-unbiased/" },
    followUp: "https://blog.juchunko.com/zh/ai-1992-consensus/",
    repoFile: "https://github.com/dAAAb/uncensored-not-unbiased/blob/main/"
  },

  /* Teaser video, one entry per language. Swap src/poster here for a new cut. */
  video: {
    zh: { src: "https://blog.juchunko.com/images/uncensored-not-unbiased/intro-zh-v2.mp4",
          poster: "https://blog.juchunko.com/images/uncensored-not-unbiased/intro-zh-v2-poster.jpg" },
    en: { src: "https://blog.juchunko.com/images/uncensored-not-unbiased/intro-en-v2.mp4",
          poster: "https://blog.juchunko.com/images/uncensored-not-unbiased/intro-en-v2-poster.jpg" }
  }
};
