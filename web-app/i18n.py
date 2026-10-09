from __future__ import annotations

from datetime import date

SUPPORTED_LANGUAGES = ("zh", "en")
DEFAULT_LANGUAGE = "zh"
LANG_COOKIE_NAME = "preferred_language"
HTML_LANG = {
    "zh": "zh-CN",
    "en": "en",
}
TRANSLATIONS = {
    "zh": {
        "language.short.zh": "中",
        "language.short.en": "EN",
        "language.zh": "中文",
        "language.en": "English",
        "nav.articles": "Articles",
        "nav.briefs": "Brief",
        "nav.about": "About",
        "nav.menu": "Menu",
        "home.greeting.morning": "早上好，hanjie",
        "home.greeting.afternoon": "下午好，hanjie",
        "home.greeting.evening": "晚上好，hanjie",
        "home.brief.all": "查看全部 {count} 条 →",
        "home.brief.archive": "查看简报归档 →",
        "docs.sidebar.browse": "浏览",
        "docs.overline.documentation": "",
        "docs.overline.section": "章节",
        "docs.page.title.articles": "文章",
        "docs.page.subtitle.root": "按分类浏览整个知识库，或者直接从最近更新的文章开始。",
        "docs.page.subtitle.section": "浏览当前分类下的子分类与文章。路径：",
        "docs.section.top_level": "主要分类",
        "docs.section.recent": "最新文章",
        "docs.section.subcategories": "子分类",
        "docs.section.articles": "文章",
        "docs.section.articles_in_section": "本节文章",
        "docs.label.sections": "个分类",
        "docs.label.items": "篇文章",
        "docs.label.articles": "篇文章",
        "docs.empty.no_articles": "这个分类下暂时没有可显示的文章。",
        "article.sidebar.section_title": "本节内容",
        "article.meta.author": "作者",
        "article.meta.published": "发布",
        "article.meta.updated": "更新",
        "article.toc.title": "本页目录",
        "article.image_preview.label": "图片预览",
        "article.image_preview.close": "关闭图片预览",
        "briefs.page.title": "Daily Brief",
        "briefs.page.heading": "每日简报",
        "briefs.page.description": "每天从计算与软件领域及少量圈外探索中筛选值得阅读的内容，减少信息噪声。",
        "briefs.language_note": "Daily Brief 正文目前仅提供中文。",
        "briefs.retention_note": "仅保留最近 14 天的简报。",
        "briefs.archive.title": "历史归档",
        "briefs.archive.ai": "技术精选",
        "briefs.archive.non_ai": "圈外",
        "briefs.items": "条内容",
        "briefs.empty.title": "最近 14 天暂无简报",
        "briefs.empty.description": "新的 Daily Brief 发布后会出现在这里。",
        "briefs.section.ai": "技术精选",
        "briefs.section.non_ai_hot": "圈外热门",
        "briefs.section.empty": "本栏目今天没有选中内容。",
        "briefs.details": "生成信息",
        "briefs.generation.materials": "材料获取：",
        "briefs.generation.sources": "摘要来源：",
        "briefs.generation.outcome": "生成情况：",
        "briefs.generation.material_result": "{source}：{status}",
        "briefs.generation.source_separator": "、",
        "briefs.generation.last_attempt": "最后尝试：{method}",
        "briefs.generation.recovery_reason": "替代获取原因：{reason}",
        "briefs.generation.unrecorded": "未记录",
        "briefs.generation.no_sources": "无",
        "briefs.generation.model_reported": "模型报告",
        "briefs.generation.source.webpage": "网页",
        "briefs.generation.source.web_metadata": "网页元信息",
        "briefs.generation.source.web_body": "网页正文",
        "briefs.generation.source.hn_post": "HN 帖子",
        "briefs.generation.source.hn_comments": "HN 评论",
        "briefs.generation.material_status.success": "成功",
        "briefs.generation.material_status.empty": "无内容",
        "briefs.generation.material_status.failed": "获取失败",
        "briefs.generation.material_status.not_attempted": "未尝试",
        "briefs.generation.material_status.not_needed": "无需获取",
        "briefs.generation.material_status.unknown": "未记录",
        "briefs.generation.status.success": "成功",
        "briefs.generation.status.insufficient": "材料不足",
        "briefs.generation.status.failed": "生成失败",
        "briefs.generation.status.not_attempted": "未尝试",
        "briefs.generation.status.unknown": "未记录",
        "briefs.generation.reason.unknown": "原因未记录",
        "briefs.generation.reason.challenge_page": "网站验证页面",
        "briefs.generation.reason.cloudflare_challenge": "Cloudflare 验证",
        "briefs.generation.reason.datadome_challenge": "DataDome 验证",
        "briefs.generation.reason.vercel_challenge": "Vercel 验证",
        "briefs.generation.reason.empty_content": "未取得有效内容",
        "briefs.generation.reason.network_timeout": "网络超时",
        "briefs.generation.reason.tls_issuer_unavailable": "TLS 证书颁发方不可用",
        "briefs.generation.reason.source_material_insufficient": "现有材料不足以生成摘要",
        "briefs.generation.reason.network_error": "网络请求失败",
        "briefs.generation.reason.http_error": "服务返回错误",
        "briefs.generation.reason.extraction_failed": "内容提取失败",
        "briefs.generation.reason.rate_limited": "请求受限或额度耗尽",
        "briefs.generation.reason.authentication_failed": "服务认证失败",
        "briefs.generation.reason.provider_unavailable": "模型服务暂不可用",
        "briefs.generation.reason.invalid_response": "模型返回内容不符合要求",
        "briefs.generation.reason.no_materials": "没有可用材料",
        "briefs.previous": "上一期",
        "briefs.next": "下一期",
        "briefs.back_to_top": "回到顶部",
        "briefs.selection_basis": "入选依据：",
        "briefs.provenance.summary_basis": "摘要依据：",
        "briefs.provenance.retrieval": "材料获取：",
        "briefs.provenance.fallback_reason": "回退原因：",
        "briefs.provenance.summary.article.original": "原文正文",
        "briefs.provenance.summary.article.archived_copy": "原文存档",
        "briefs.provenance.summary.article.same_article": "同一篇文章",
        "briefs.provenance.summary.article.syndicated_copy": "同稿转载",
        "briefs.provenance.summary.article.alternate_reporting": "同一事件的其他报道",
        "briefs.provenance.summary.source_and_comments": "页面或帖子材料与部分 HN 评论",
        "briefs.provenance.summary.hn_comments": "部分 HN 评论",
        "briefs.provenance.summary.hn_post": "HN 帖子",
        "briefs.provenance.summary.video_captions": "视频字幕",
        "briefs.provenance.method.direct": "直接请求",
        "briefs.provenance.method.jina": "Jina Reader",
        "briefs.provenance.method.wayback": "Wayback Machine",
        "briefs.provenance.method.github_readme": "GitHub README",
        "briefs.provenance.method.github_raw": "GitHub Raw",
        "briefs.provenance.method.youtube_caption": "YouTube 字幕",
        "briefs.provenance.method.story_text": "HN 帖子内容",
        "briefs.provenance.retrieval.success": "通过 {method} 取得",
        "briefs.provenance.retrieval.failed": "未取得（最后尝试：{method}）",
        "briefs.provenance.fallback.challenge_page": "网站验证页面",
        "briefs.provenance.fallback.cloudflare_challenge": "Cloudflare 验证",
        "briefs.provenance.fallback.datadome_challenge": "DataDome 验证",
        "briefs.provenance.fallback.vercel_challenge": "Vercel 验证",
        "briefs.provenance.fallback.empty_content": "未取得有效正文",
        "briefs.provenance.fallback.network_timeout": "网络超时",
        "briefs.provenance.fallback.tls_issuer_unavailable": "TLS 证书颁发方不可用",
        "briefs.provenance.fallback.source_material_insufficient": "材料不足以生成摘要",
        "briefs.discussion": "HN 讨论",
        "briefs.points": "points",
        "briefs.comments": "条评论",
        "about.hero.overline": "PROFILE / HIRING PAGE",
        "about.hero.subtitle": "Cloud / DevOps / Full-stack",
        "about.hero.copy1": "我目前把精力放在云基础设施、自动化部署与 Python 工程实践上，持续通过个人项目把 Terraform、Docker、Linux、Nginx、Python Flask 和 GCP / Azure 串成一条完整链路。",
        "about.hero.copy2": "最近的 AI 相当好用，我会使用 LLM / agent 工作流辅助调研、调试、重构与文档整理，例如 Codex 这一类 coding agent。",
        "about.hero.copy3": "我正在寻找偏 Cloud / DevOps / Full-stack 方向的机会，也愿意承担需要较强执行力、学习能力和工程落地能力的初中级岗位。",
        "about.hero.resume": "Download Resume",
        "about.hero.resume_note": "Coming Soon",
        "about.hero.contact": "Contact Me",
        "about.status.focus": "Focus",
        "about.status.focus_value": "Cloud / DevOps / Full-stack",
        "about.status.status": "Status",
        "about.status.status_value": "Open to opportunities",
        "about.status.location": "Location",
        "about.status.location_value": "Shanghai CN / Remote-friendly",
        "about.who.overline": "我是谁",
        "about.who.title": "我是谁",
        "about.who.p1": "我目前处于职业起步阶段，正在通过真实项目、部署实践和持续写作，逐步建立自己的作品集与工程判断力。",
        "about.who.p2": "当前的主线方向是 Cloud / DevOps / Full-stack，重点放在基础设施、部署链路、Python 服务和可重复交付。",
        "about.who.p3": "我希望进入一个能持续做工程落地、系统学习并承担真实责任的团队，而不是只停留在表层使用技术。",
        "about.who.p4": "相比单点炫技，我更看重把学习、实现、记录和复盘串成闭环，并长期积累成可以证明能力的成果。",
        "about.how.overline": "我如何工作",
        "about.how.title": "我如何工作",
        "about.how.p1": "我喜欢把零散的问题整理成可以复用的工程方案，而不是只停留在“跑通一次”。",
        "about.how.p2": "我擅长通过文档化、脚本化和环境重建，去验证自己是否真正理解一个技术问题。",
        "about.how.p3": "我当前最关注的主题是基础设施自动化、Linux 系统实践、容器化部署，以及云平台上的可重复交付。",
        "about.how.p4": "对我来说，写文档和做项目不是分开的两件事，它们共同构成了我理解技术和证明能力的方式。",
        "about.work.overline": "我在做什么",
        "about.work.title": "我在做什么",
        "about.work.card1.title": "基础设施自动化",
        "about.work.card1.desc": "使用 Terraform 组织云资源配置，关注可重复部署、环境一致性和基础设施变更的可追踪性。",
        "about.work.card2.title": "Python 后端与 AI 辅助交付",
        "about.work.card2.desc": "使用 Flask 构建实际可运行的服务，同时熟练把 Codex 这类 agent 纳入调试、重构、脚本整理与文档产出流程。",
        "about.work.card3.title": "Linux / Docker / Nginx",
        "about.work.card3.desc": "围绕 Linux、容器和反向代理做真实部署实践，关心服务编排、静态资源、WAF、日志和生产链路稳定性。",
        "about.projects.overline": "代表项目",
        "about.projects.title": "代表项目",
        "about.projects.featured.title": "生产风格的个人网站系统",
        "about.projects.featured.desc": "这个项目并不只是一个个人主页，而是一套完整的内容发布与部署系统：使用 Flask 提供页面和内部接口，通过 Markdown 渲染、文章同步与数据库索引完成内容发布，再结合 Docker Compose、Nginx、Cloudflare、GCP 和 GitHub Actions 形成一条可以持续迭代的上线链路。",
        "about.current.overline": "当前状态",
        "about.current.title": "当前状态",
        "about.current.card1.title": "职业阶段",
        "about.current.card1.desc": "职业起步阶段，正在持续通过项目与文档构建作品集。",
        "about.current.card2.title": "学习方向",
        "about.current.card2.desc": "以项目驱动自学为主，重点补强 Linux、网络、云平台和自动化工程实践。",
        "about.current.card3.title": "目标岗位",
        "about.current.card3.desc": "Cloud / DevOps / Infrastructure 方向，也接受需要较强工程执行力的后端与平台类岗位。",
        "about.current.card4.title": "可投入状态",
        "about.current.card4.desc": "目前正在积极寻找机会，愿意尽快进入真实业务环境持续成长。",
        "about.write.overline": "为什么写博客",
        "about.write.title": "为什么写博客",
        "about.write.p1": "为什么要写博客？为什么要建立个人网站？",
        "about.write.p2": "如果根本就没人来读它们，这个网站和这些文章又有什么意义？在 AI 如此强大而且越来越强大的今天，还需要写技术文章吗？直接问 AI 不香吗？",
        "about.write.p3": "写技术文章会不会就是浪费时间呢？",
        "about.write.p4": "对我来说，写作本身就是学习与理解的一部分。因为我在思考、学习和成长，我希望把这些东西记录在某个地方。",
        "about.write.p5": "记录遇到的问题，询问各个 AI，理解问题背后的原理，尽量让文章逻辑通顺、循序渐进，并包含案例、详解和截图，方便读者理解。",
        "about.write.p6": "所以写博客不是为了有人来看我的文章，而是为了我自己的需要，方便我建立自己的知识库，也方便我在遇到相同或相似问题时回顾和查看。",
        "about.write.p7": "博客的目标读者并不是我的观众，而是未来的我；或许未来有一天某个真正需要这些文章的人，或者 AI，也会看到它。",
        "about.write.p8": "如果有人读了，那就更好。如果没有，那它们也已经完成了自己的意义。",
        "about.contact.overline": "联系我",
        "about.contact.title": "联系我",
        "about.contact.email": "EMAIL",
        "about.contact.github": "GitHub",
        "error.404.title": "页面不存在",
        "error.404.heading": "页面不存在",
        "error.404.body": "你访问的地址不存在。请检查链接，或返回站点首页继续浏览。",
    },
    "en": {
        "language.short.zh": "中",
        "language.short.en": "EN",
        "language.zh": "中文",
        "language.en": "English",
        "nav.articles": "Articles",
        "nav.briefs": "Brief",
        "nav.about": "About",
        "nav.menu": "Menu",
        "home.greeting.morning": "Good morning, hanjie",
        "home.greeting.afternoon": "Good afternoon, hanjie",
        "home.greeting.evening": "Good evening, hanjie",
        "home.brief.all": "See all {count} →",
        "home.brief.archive": "Open the archive →",
        "docs.sidebar.browse": "Browse",
        "docs.overline.documentation": "",
        "docs.overline.section": "Section",
        "docs.page.title.articles": "Articles",
        "docs.page.subtitle.root": "Browse the full knowledge base by category, or start with the most recently updated articles.",
        "docs.page.subtitle.section": "Browse subcategories and articles under the current section. Path:",
        "docs.section.top_level": "Top-Level Categories",
        "docs.section.recent": "Recent Articles",
        "docs.section.subcategories": "Subcategories",
        "docs.section.articles": "Articles",
        "docs.section.articles_in_section": "Articles in This Section",
        "docs.label.sections": "sections",
        "docs.label.items": "items",
        "docs.label.articles": "articles",
        "docs.empty.no_articles": "There are no displayable articles in this section yet.",
        "article.sidebar.section_title": "In This Section",
        "article.meta.author": "Author",
        "article.meta.published": "Published",
        "article.meta.updated": "Updated",
        "article.toc.title": "On This Page",
        "article.image_preview.label": "Image preview",
        "article.image_preview.close": "Close image preview",
        "briefs.page.title": "Daily Brief",
        "briefs.page.heading": "Daily Brief",
        "briefs.page.description": "A small daily selection from computing and software, plus a few beyond-the-bubble discoveries, curated to reduce information noise.",
        "briefs.language_note": "Daily Brief entries are currently published in Chinese only.",
        "briefs.retention_note": "Only briefs from the last 14 days are retained.",
        "briefs.archive.title": "Archive",
        "briefs.archive.ai": "Tech picks",
        "briefs.archive.non_ai": "Beyond",
        "briefs.items": "items",
        "briefs.empty.title": "No briefs in the last 14 days",
        "briefs.empty.description": "New Daily Brief editions will appear here when published.",
        "briefs.section.ai": "Tech picks",
        "briefs.section.non_ai_hot": "Beyond the bubble",
        "briefs.section.empty": "No items were selected for this section today.",
        "briefs.details": "Generation info",
        "briefs.generation.materials": "Material retrieval:",
        "briefs.generation.sources": "Summary sources:",
        "briefs.generation.outcome": "Generation:",
        "briefs.generation.material_result": "{source}: {status}",
        "briefs.generation.source_separator": ", ",
        "briefs.generation.last_attempt": "Last attempt: {method}",
        "briefs.generation.recovery_reason": "Recovery reason: {reason}",
        "briefs.generation.unrecorded": "Not recorded",
        "briefs.generation.no_sources": "None",
        "briefs.generation.model_reported": "Reported by the model",
        "briefs.generation.source.webpage": "Webpage",
        "briefs.generation.source.web_metadata": "Page metadata",
        "briefs.generation.source.web_body": "Webpage body",
        "briefs.generation.source.hn_post": "HN post",
        "briefs.generation.source.hn_comments": "HN comments",
        "briefs.generation.material_status.success": "Retrieved",
        "briefs.generation.material_status.empty": "No content",
        "briefs.generation.material_status.failed": "Failed",
        "briefs.generation.material_status.not_attempted": "Not attempted",
        "briefs.generation.material_status.not_needed": "Not needed",
        "briefs.generation.material_status.unknown": "Not recorded",
        "briefs.generation.status.success": "Succeeded",
        "briefs.generation.status.insufficient": "Insufficient material",
        "briefs.generation.status.failed": "Failed",
        "briefs.generation.status.not_attempted": "Not attempted",
        "briefs.generation.status.unknown": "Not recorded",
        "briefs.generation.reason.unknown": "Reason not recorded",
        "briefs.generation.reason.challenge_page": "Site challenge page",
        "briefs.generation.reason.cloudflare_challenge": "Cloudflare challenge",
        "briefs.generation.reason.datadome_challenge": "DataDome challenge",
        "briefs.generation.reason.vercel_challenge": "Vercel challenge",
        "briefs.generation.reason.empty_content": "No usable content retrieved",
        "briefs.generation.reason.network_timeout": "Network timeout",
        "briefs.generation.reason.tls_issuer_unavailable": "TLS issuer unavailable",
        "briefs.generation.reason.source_material_insufficient": "Available material does not support a summary",
        "briefs.generation.reason.network_error": "Network request failed",
        "briefs.generation.reason.http_error": "Service returned an HTTP error",
        "briefs.generation.reason.extraction_failed": "Content extraction failed",
        "briefs.generation.reason.rate_limited": "Rate or quota limit reached",
        "briefs.generation.reason.authentication_failed": "Service authentication failed",
        "briefs.generation.reason.provider_unavailable": "Model service unavailable",
        "briefs.generation.reason.invalid_response": "Invalid model response",
        "briefs.generation.reason.no_materials": "No available material",
        "briefs.previous": "Previous brief",
        "briefs.next": "Next brief",
        "briefs.back_to_top": "Back to top",
        "briefs.selection_basis": "Selection basis:",
        "briefs.provenance.summary_basis": "Summary based on:",
        "briefs.provenance.retrieval": "Material retrieval:",
        "briefs.provenance.fallback_reason": "Fallback reason:",
        "briefs.provenance.summary.article.original": "original article",
        "briefs.provenance.summary.article.archived_copy": "archived copy of the article",
        "briefs.provenance.summary.article.same_article": "the same article",
        "briefs.provenance.summary.article.syndicated_copy": "a syndicated copy",
        "briefs.provenance.summary.article.alternate_reporting": "alternate reporting on the same event",
        "briefs.provenance.summary.source_and_comments": "page or post material and selected HN comments",
        "briefs.provenance.summary.hn_comments": "selected HN comments",
        "briefs.provenance.summary.hn_post": "the HN post",
        "briefs.provenance.summary.video_captions": "video captions",
        "briefs.provenance.method.direct": "direct request",
        "briefs.provenance.method.jina": "Jina Reader",
        "briefs.provenance.method.wayback": "Wayback Machine",
        "briefs.provenance.method.github_readme": "GitHub README",
        "briefs.provenance.method.github_raw": "GitHub Raw",
        "briefs.provenance.method.youtube_caption": "YouTube captions",
        "briefs.provenance.method.story_text": "HN post text",
        "briefs.provenance.retrieval.success": "retrieved via {method}",
        "briefs.provenance.retrieval.failed": "not retrieved (last attempt: {method})",
        "briefs.provenance.fallback.challenge_page": "site challenge page",
        "briefs.provenance.fallback.cloudflare_challenge": "Cloudflare challenge",
        "briefs.provenance.fallback.datadome_challenge": "DataDome challenge",
        "briefs.provenance.fallback.vercel_challenge": "Vercel challenge",
        "briefs.provenance.fallback.empty_content": "no usable article content",
        "briefs.provenance.fallback.network_timeout": "network timeout",
        "briefs.provenance.fallback.tls_issuer_unavailable": "TLS issuer unavailable",
        "briefs.provenance.fallback.source_material_insufficient": "insufficient source material for a summary",
        "briefs.discussion": "HN Discussion",
        "briefs.points": "points",
        "briefs.comments": "comments",
        "about.hero.overline": "Profile / Hiring Page",
        "about.hero.subtitle": "Cloud / DevOps / Full-stack",
        "about.hero.copy1": "I am currently focusing on cloud infrastructure, deployment automation, and Python engineering practice, using personal projects to connect Terraform, Docker, Linux, Nginx, Python Flask, and GCP / Azure into one end-to-end workflow.",
        "about.hero.copy2": "Recent AI tooling has been genuinely useful for me. I use LLM / agent workflows to support research, debugging, refactoring, and documentation work, including coding agents such as Codex.",
        "about.hero.copy3": "I am looking for opportunities in Cloud / DevOps / Full-stack work and am also open to junior-to-mid-level roles that require strong execution, learning ability, and practical engineering delivery.",
        "about.hero.resume": "Download Resume",
        "about.hero.resume_note": "Coming Soon",
        "about.hero.contact": "Contact Me",
        "about.status.focus": "Focus",
        "about.status.focus_value": "Cloud / DevOps / Full-stack",
        "about.status.status": "Status",
        "about.status.status_value": "Open to opportunities",
        "about.status.location": "Location",
        "about.status.location_value": "Shanghai CN / Remote-friendly",
        "about.who.overline": "Who I Am",
        "about.who.title": "Who I Am",
        "about.who.p1": "I am still early in my career and using real projects, deployment practice, and sustained writing to build both a portfolio and stronger engineering judgment.",
        "about.who.p2": "My main direction right now is Cloud / DevOps / Full-stack, with most of my effort going into infrastructure, deployment flows, Python services, and repeatable delivery.",
        "about.who.p3": "I want to join a team where I can keep shipping real engineering work, learn systematically, and take on real responsibility instead of staying at the surface level of tools.",
        "about.who.p4": "More than isolated technical tricks, I care about connecting learning, implementation, documentation, and retrospection into a loop that compounds into proof of ability.",
        "about.how.overline": "How I Work",
        "about.how.title": "How I Work",
        "about.how.p1": "I like turning scattered problems into reusable engineering solutions instead of stopping at 'it worked once.'",
        "about.how.p2": "I rely heavily on documentation, scripts, and environment rebuilds to verify whether I truly understand a technical problem.",
        "about.how.p3": "The topics I care most about right now are infrastructure automation, Linux systems practice, containerized deployment, and repeatable delivery on cloud platforms.",
        "about.how.p4": "For me, writing documentation and building projects are not separate activities. Together they form how I understand technology and demonstrate capability.",
        "about.work.overline": "What I Work With",
        "about.work.title": "What I Work With",
        "about.work.card1.title": "Infrastructure Automation",
        "about.work.card1.desc": "I use Terraform to organize cloud resource configuration, with a focus on repeatable deployment, environment consistency, and traceable infrastructure changes.",
        "about.work.card2.title": "Python Backend & AI-assisted Delivery",
        "about.work.card2.desc": "I build runnable services with Flask while also folding agents like Codex into debugging, refactoring, script cleanup, and documentation workflows.",
        "about.work.card3.title": "Linux / Docker / Nginx",
        "about.work.card3.desc": "I do real deployment practice around Linux, containers, and reverse proxies, with attention to orchestration, static assets, WAF, logging, and production-path stability.",
        "about.projects.overline": "Featured Projects",
        "about.projects.title": "Featured Projects",
        "about.projects.featured.title": "Personal Website as a Production-style System",
        "about.projects.featured.desc": "This project is not just a personal homepage. It is a complete content publishing and deployment system: Flask serves pages and internal endpoints, Markdown rendering and article sync feed the publishing flow, and Docker Compose, Nginx, Cloudflare, GCP, and GitHub Actions form an end-to-end release path that can keep evolving.",
        "about.current.overline": "Current Status",
        "about.current.title": "Current Status",
        "about.current.card1.title": "Career Stage",
        "about.current.card1.desc": "Early career stage, steadily building a portfolio through projects and documentation.",
        "about.current.card2.title": "Learning Track",
        "about.current.card2.desc": "Mainly self-directed learning through projects, with focused work on Linux, networking, cloud platforms, and automation engineering practice.",
        "about.current.card3.title": "Target Role",
        "about.current.card3.desc": "Cloud / DevOps / Infrastructure roles, and also backend or platform roles that need strong engineering execution.",
        "about.current.card4.title": "Availability",
        "about.current.card4.desc": "Actively looking for opportunities and ready to grow quickly inside a real production environment.",
        "about.write.overline": "Why I Write",
        "about.write.title": "Why I Write",
        "about.write.p1": "Why write a blog? Why build a personal website?",
        "about.write.p2": "If no one reads it, what is the point of the site and the articles? In a world where AI is already powerful and getting stronger, do we still need technical writing? Isn't asking AI enough?",
        "about.write.p3": "Is writing technical articles just a waste of time?",
        "about.write.p4": "For me, writing itself is part of learning and understanding. I am thinking, learning, and growing, and I want to record those things somewhere.",
        "about.write.p5": "I document problems I run into, ask different AI systems, work to understand the principles underneath, and try to make each article logical, progressive, and packed with examples, explanation, and screenshots that help readers follow along.",
        "about.write.p6": "So I do not write primarily because I expect people to read my articles. I write because I need a personal knowledge base that I can return to when I hit the same or similar problems again.",
        "about.write.p7": "The audience for this blog is not really 'my audience' but my future self. Maybe one day someone who truly needs these articles, or even an AI, will find them useful too.",
        "about.write.p8": "If people read them, great. If not, they still would have already served their purpose.",
        "about.contact.overline": "Contact",
        "about.contact.title": "Contact",
        "about.contact.email": "Email",
        "about.contact.github": "GitHub",
        "error.404.title": "Page Not Found",
        "error.404.heading": "Page Not Found",
        "error.404.body": "The requested URL was not found. Please check the link or return to the site homepage.",
    },
}


def normalize_language(value: str | None) -> str | None:
    if not value:
        return None

    normalized = value.strip().lower().replace("_", "-")
    if normalized.startswith("zh"):
        return "zh"
    if normalized.startswith("en"):
        return "en"
    return None


def get_language_from_cookie(raw_cookie: str | None) -> str | None:
    return normalize_language(raw_cookie)


def get_language_from_header(raw_header: str | None) -> str | None:
    if not raw_header:
        return None

    candidates = []
    for position, item in enumerate(raw_header.split(",")):
        token = item.strip()
        if not token:
            continue

        parts = [part.strip() for part in token.split(";") if part.strip()]
        language_tag = parts[0]
        quality = 1.0

        for part in parts[1:]:
            if part.startswith("q="):
                try:
                    quality = float(part[2:])
                except ValueError:
                    quality = 0.0
                break

        normalized = normalize_language(language_tag)
        if normalized:
            candidates.append((quality, position, normalized))

    if not candidates:
        return None

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return candidates[0][2]


def resolve_preferred_language(
    cookie_value: str | None, accept_language_header: str | None
) -> str:
    cookie_language = get_language_from_cookie(cookie_value)
    if cookie_language:
        return cookie_language

    header_language = get_language_from_header(accept_language_header)
    if header_language:
        return header_language

    return DEFAULT_LANGUAGE


def html_lang_code(lang: str | None) -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    return HTML_LANG.get(normalized, HTML_LANG[DEFAULT_LANGUAGE])


def get_language_from_path(path: str | None) -> str | None:
    if not path:
        return None

    first_segment = path.lstrip("/").split("/", 1)[0]
    if first_segment in SUPPORTED_LANGUAGES:
        return first_segment

    return None


def public_path(lang: str, suffix: str = "") -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    suffix = suffix or ""
    if suffix and not suffix.startswith("/"):
        suffix = f"/{suffix}"
    if not suffix:
        return f"/{normalized}/"
    return f"/{normalized}{suffix}"


def alternate_language(lang: str) -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    return "en" if normalized == "zh" else "zh"


def switch_language_path(path: str, target_lang: str) -> str:
    parts = [segment for segment in path.split("/") if segment]
    if parts and parts[0] in SUPPORTED_LANGUAGES:
        suffix = "/".join(parts[1:])
        return public_path(target_lang, suffix)
    return public_path(target_lang)


def translate(lang: str | None, key: str, fallback: str | None = None) -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    return TRANSLATIONS.get(normalized, {}).get(
        key, fallback if fallback is not None else key
    )


ZH_WEEKDAYS = "一二三四五六日"
EN_WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
EN_MONTHS = (
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def format_day(day: date, lang: str | None, *, weekday: bool = True) -> str:
    """Return a short calendar label such as "10月6日 星期二" or "Tue, Oct 6"."""
    if normalize_language(lang) == "en":
        label = f"{EN_MONTHS[day.month - 1]} {day.day}"
        return f"{EN_WEEKDAYS[day.weekday()]}, {label}" if weekday else label
    label = f"{day.month}月{day.day}日"
    return f"{label} 星期{ZH_WEEKDAYS[day.weekday()]}" if weekday else label
