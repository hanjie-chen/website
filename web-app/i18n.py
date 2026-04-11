from __future__ import annotations

from typing import Optional

SUPPORTED_LANGUAGES = ("zh", "en")
DEFAULT_LANGUAGE = "zh"
LANG_COOKIE_NAME = "preferred_language"
HTML_LANG = {
    "zh": "zh-CN",
    "en": "en",
}
TRANSLATIONS = {
    "zh": {
        "language.zh": "中文",
        "language.en": "English",
        "nav.home": "首页",
        "nav.articles": "文章",
        "nav.about": "关于我",
        "footer.copy": "翰杰个人站",
        "home.nav.brand": "欢迎来到我的个人网站",
        "home.hero.overline": "个人网站 / 知识库",
        "home.hero.title": "构建、学习、记录。",
        "home.hero.lead": "这里记录我的工程实践、技术笔记和持续构建中的项目。",
        "home.hero.support": "内容主要围绕 Cloud、DevOps、Full-stack、Python，以及 AI-assisted workflow。",
        "home.hero.primary_cta": "阅读文章",
        "home.hero.secondary_cta": "关于我",
        "home.start.overline": "从这里开始",
        "home.start.title": "你可以在这里看到什么",
        "home.start.articles_title": "文章",
        "home.start.articles_desc": "技术笔记、部署记录、实践文章，以及围绕 Cloud / DevOps / Full-stack 的持续整理。",
        "home.start.about_title": "关于我",
        "home.start.about_desc": "更完整的个人介绍、当前关注点、工作方式，以及与求职相关的信息。",
        "home.focus.overline": "当前关注",
        "home.focus.title": "当前关注",
        "home.focus.cloud_title": "云 / DevOps",
        "home.focus.cloud_desc": "围绕 Terraform、GCP、Cloudflare 和部署工作流持续实践。",
        "home.focus.fullstack_title": "全栈 / Python",
        "home.focus.fullstack_desc": "围绕 Flask、后端服务和容器化应用持续构建。",
        "home.focus.ai_title": "AI 辅助工作流",
        "home.focus.ai_desc": "使用 LLM 和 agent 工具辅助调试、重构与文档整理。",
        "home.note.overline": "为什么做这个网站",
        "home.note.title": "为什么做这个网站",
        "home.note.p1": "这个网站既是我的技术知识库，也是我整理项目、验证理解和持续输出的地方。",
        "home.note.p2": "我希望它是一个长期可维护、可复用、可迭代的工程记录，而不只是零散文章的集合。",
        "about.nav.brand": "关于我",
        "about.hero.overline": "个人简介 / 求职页面",
        "about.hero.subtitle": "Cloud / DevOps / Full-stack",
        "about.hero.copy1": "我目前把精力放在云基础设施、自动化部署与 Python 工程实践上，持续通过个人项目把 Terraform、Docker、Linux、Nginx、Python Flask 和 GCP / Azure 串成一条完整链路。",
        "about.hero.copy2": "最近的 AI 相当好用，我会使用 LLM / agent 工作流辅助调研、调试、重构与文档整理，例如 Codex 这一类 coding agent。",
        "about.hero.copy3": "我正在寻找偏 Cloud / DevOps / Full-stack 方向的机会，也愿意承担需要较强执行力、学习能力和工程落地能力的初中级岗位。",
        "about.hero.resume": "下载简历",
        "about.hero.resume_note": "敬请期待",
        "about.hero.contact": "联系我",
        "about.status.focus": "关注方向",
        "about.status.focus_value": "Cloud / DevOps / Full-stack",
        "about.status.status": "状态",
        "about.status.status_value": "正在寻找机会",
        "about.status.location": "地点",
        "about.status.location_value": "中国上海 / 支持远程",
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
        "about.projects.live": "在线站点",
        "about.projects.source": "源代码",
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
        "about.contact.email": "邮箱",
        "about.contact.github": "GitHub",
        "error.404.title": "页面不存在",
        "error.404.heading": "页面不存在",
        "error.404.body": "你访问的地址不存在。请检查链接，或返回站点首页继续浏览。",
    },
    "en": {
        "language.zh": "中文",
        "language.en": "English",
        "nav.home": "Home",
        "nav.articles": "Articles",
        "nav.about": "About Me",
        "footer.copy": "for hanjie site",
        "home.nav.brand": "Welcome to my personal website",
        "home.hero.overline": "PERSONAL SITE / KNOWLEDGE BASE",
        "home.hero.title": "Build, Learn, Document.",
        "home.hero.lead": "This site is where I document engineering practice, technical notes, and projects that are still actively being built.",
        "home.hero.support": "Most of the content revolves around cloud, DevOps, full-stack work, Python, and AI-assisted workflow.",
        "home.hero.primary_cta": "Read Articles",
        "home.hero.secondary_cta": "About Me",
        "home.start.overline": "START HERE",
        "home.start.title": "What you'll find here",
        "home.start.articles_title": "Articles",
        "home.start.articles_desc": "Technical notes, deployment records, hands-on articles, and an ongoing body of work around Cloud / DevOps / Full-stack.",
        "home.start.about_title": "About Me",
        "home.start.about_desc": "A fuller personal profile, current focus areas, how I work, and job-search related context.",
        "home.focus.overline": "CURRENT FOCUS",
        "home.focus.title": "Current Focus",
        "home.focus.cloud_title": "Cloud / DevOps",
        "home.focus.cloud_desc": "Terraform, GCP, Cloudflare, and deployment workflows.",
        "home.focus.fullstack_title": "Full-stack / Python",
        "home.focus.fullstack_desc": "Flask, backend services, and containerized applications.",
        "home.focus.ai_title": "AI-assisted workflow",
        "home.focus.ai_desc": "Using LLM and agent tools to support debugging, refactoring, and documentation.",
        "home.note.overline": "WHY THIS SITE EXISTS",
        "home.note.title": "Why This Site Exists",
        "home.note.p1": "This site is both my technical knowledge base and a place where I organize projects, validate understanding, and keep shipping written output.",
        "home.note.p2": "I want it to be a long-lived engineering record that is maintainable, reusable, and iterative, not just a pile of disconnected articles.",
        "about.nav.brand": "About Me",
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
        "about.projects.live": "Live Site",
        "about.projects.source": "Source Code",
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


def normalize_language(value: Optional[str]) -> Optional[str]:
    if not value:
        return None

    normalized = value.strip().lower().replace("_", "-")
    if normalized.startswith("zh"):
        return "zh"
    if normalized.startswith("en"):
        return "en"
    return None


def get_language_from_cookie(raw_cookie: Optional[str]) -> Optional[str]:
    return normalize_language(raw_cookie)


def get_language_from_header(raw_header: Optional[str]) -> Optional[str]:
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
    cookie_value: Optional[str], accept_language_header: Optional[str]
) -> str:
    cookie_language = get_language_from_cookie(cookie_value)
    if cookie_language:
        return cookie_language

    header_language = get_language_from_header(accept_language_header)
    if header_language:
        return header_language

    return DEFAULT_LANGUAGE


def html_lang_code(lang: Optional[str]) -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    return HTML_LANG.get(normalized, HTML_LANG[DEFAULT_LANGUAGE])


def get_language_from_path(path: Optional[str]) -> Optional[str]:
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


def translate(lang: Optional[str], key: str, fallback: Optional[str] = None) -> str:
    normalized = normalize_language(lang) or DEFAULT_LANGUAGE
    return TRANSLATIONS.get(normalized, {}).get(
        key, fallback if fallback is not None else key
    )
