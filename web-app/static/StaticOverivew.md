# Static文件夹简介

静态文件（static files）和我们的模板概念相反，指的是内容不需要动态生成的文件。比如图片、CSS 文件和 JavaScript 脚本等。

在 HTML 文件里，引入这些静态文件需要给出资源所在的 URL。为了更加灵活，这些文件的 URL 可以通过 Flask 提供的 `url_for()` 函数来生成。在 Python 脚本里，`url_for()` 函数需要从 `flask` 包中导入，而在模板中则可以直接使用，因为 Flask 把一些常用的函数和对象添加到了模板上下文（环境）里。

在 Flask 中，我们需要创建一个 static 文件夹来保存静态文件，它应该和程序模块、templates 文件夹在同一目录层级

其中 favicon_point.ico（蓝色圆点）是网站当前的图标，顶栏品牌名前的圆点标志与它保持一致

## CSS框架:Bootstrap5

决定了使用Bootstrap来弄CSS完成好看的网站搭建，适合我这种一个人搭建的网站。发现有两种方式来使用bootstrap，一个是使用CDN链接的方式，让其去加载网络上面的bootstrap文件，一个是本地下载bootstrap文件。当然以学习为目的来使用bootstrap，我选择将其下载到本地上面。

> 通过在HTML中使用CDN链接的方式使用Bootstrap和使用自己在本地下载的Bootstrap文件相比，主要区别在于：
>
> 1. 下载速度：使用CDN链接可以节省您下载和部署Bootstrap的时间和成本，因为浏览器会从CDN服务器上获取所需的CSS样式和JavaScript组件。而如果您使用本地下载的Bootstrap文件，则需要等待文件下载完毕并将其放置到正确的目录下，才能开始使用。
>
> 2. 可靠性：如果您使用CDN链接，则可以确保您的网站每次都使用最新版本的Bootstrap库，而不必担心您的本地文件是否过时或受到漏洞攻击。同时，由于CDN服务器分布在全球各地，因此您的用户可以更快地加载您的网站，提高用户体验。
>
> 3. 网络连接：如果您使用CDN链接，则需要访问外部服务器来获取Bootstrap文件，这意味着您的网站的可用性和性能可能会受到网络状况的影响。如果您使用本地下载的Bootstrap文件，则无需依赖网络连接，因此可以更加可靠和稳定。
>
> 总的来说，使用CDN链接的方式更加方便和快捷，但是使用本地下载的Bootstrap文件则更加稳定和可控。具体选择取决于您的实际需求和环境。

### Bootstrap-5.3.0

将下载的bootstrap压缩包解压到static文件夹下面，即可使用bootstrap5。包含如下文件

```shell
bootstrap5/
├── css/
│   ├── bootstrap-grid.css
│   ├── bootstrap-grid.css.map
│   ├── bootstrap-grid.min.css
│   ├── bootstrap-grid.min.css.map
│   ├── bootstrap-grid.rtl.css
│   ├── bootstrap-grid.rtl.css.map
│   ├── bootstrap-grid.rtl.min.css
│   ├── bootstrap-grid.rtl.min.css.map
│   ├── bootstrap-reboot.css
│   ├── bootstrap-reboot.css.map
│   ├── bootstrap-reboot.min.css
│   ├── bootstrap-reboot.min.css.map
│   ├── bootstrap-reboot.rtl.css
│   ├── bootstrap-reboot.rtl.css.map
│   ├── bootstrap-reboot.rtl.min.css
│   ├── bootstrap-reboot.rtl.min.css.map
│   ├── bootstrap-utilities.css
│   ├── bootstrap-utilities.css.map
│   ├── bootstrap-utilities.min.css
│   ├── bootstrap-utilities.min.css.map
│   ├── bootstrap-utilities.rtl.css
│   ├── bootstrap-utilities.rtl.css.map
│   ├── bootstrap-utilities.rtl.min.css
│   ├── bootstrap-utilities.rtl.min.css.map
│   ├── bootstrap.css
│   ├── bootstrap.css.map
│   ├── bootstrap.min.css
│   ├── bootstrap.min.css.map
│   ├── bootstrap.rtl.css
│   ├── bootstrap.rtl.css.map
│   ├── bootstrap.rtl.min.css
│   └── bootstrap.rtl.min.css.map
└── js/
    ├── bootstrap.bundle.js
    ├── bootstrap.bundle.js.map
    ├── bootstrap.bundle.min.js
    ├── bootstrap.bundle.min.js.map
    ├── bootstrap.esm.js
    ├── bootstrap.esm.js.map
    ├── bootstrap.esm.min.js
    ├── bootstrap.esm.min.js.map
    ├── bootstrap.js
    ├── bootstrap.js.map
    ├── bootstrap.min.js
    └── bootstrap.min.js.map

```



## 字体Font

中文使用苹方简体`PingFangSC`英文使用Jetbrain开发的IDE字体`Jetbrain Mono`并且提供2种格式的加载方式，让浏览器自行选择。

## style.css 文件说明
CSS 中选择器的不同类型及其作用：

1. **元素选择器**（Element Selector）：
   - `body` 是一个元素选择器，它直接选中 HTML 中的 `<body>` 元素，并应用样式规则到该元素及其所有子元素。
   - 例如：
     ```css
     body {
         color: #DBDCE2;
     }
     ```
     这段代码会将整个页面中所有文字的颜色设置为 `#DBDCE2`，因为它是直接选中 `<body>` 元素。

2. **类选择器**（Class Selector）：
   - `.body_background` 是一个类选择器，它选中所有具有 `body_background` 类的元素，并应用样式规则到这些元素。
   - 类选择器前面有一个点号（`.`），用于区分它是一个类选择器。
   - 例如：
     ```css
     .body_background {
         background-color: #1A1C1F;
     }
     ```
     这段代码会将所有具有 `body_background` 类的元素的背景颜色设置为 `#1A1C1F`。

### 作用与区别

- **元素选择器**：直接选中指定的 HTML 元素并应用样式。它不需要前缀。例如，`body` 选择器会应用到 `<body>` 元素。
- **类选择器**：选中所有具有指定类的元素，并应用样式。它需要用点号（`.`）作为前缀。例如，`.body_background` 会应用到所有具有 `body_background` 类的元素。

## search.js 文件说明
用于触发 search bar自动变长，参考github search bar,可能还需要改进

您提出了一个非常好的问题，这让我们可以深入了解SVG的本质。让我来详细解答您的疑问：

## SVG的本质：
   是的，SVG（Scalable Vector Graphics）的本质确实是一段代码。具体来说，它是一种基于XML的标记语言，用于描述二维矢量图形。

2. SVG的工作原理：
   - SVG使用XML格式的文本来描述图像的各个部分。
   - 浏览器或其他支持SVG的软件会解析这些代码，然后根据描述绘制出图形。
   - 这就是为什么SVG图像可以无损放大 - 因为它们是通过数学公式定义的，而不是像素点。

3. 关于 "http://www.w3.org/2000/svg"：
   - 这个URL出现在SVG的xmlns属性中：`xmlns="http://www.w3.org/2000/svg"`
   - xmlns 代表 "XML Namespace"（XML命名空间）。
   - 这个URL不是一个你需要访问的网页，而是一个标识符，用来告诉解析器这个文档使用的是SVG规范。
   - W3C（World Wide Web Consortium）是制定Web标准的国际组织，他们定义了SVG规范。

4. SVG代码的主要部分：
   - `<svg>` 是根元素，定义了SVG图像的容器。
   - `width` 和 `height` 属性定义了SVG的尺寸。
   - `viewBox` 定义了SVG坐标系统。
   - `<path>` 元素用于定义路径，这里描述了房子的形状。
   - `d` 属性包含了一系列命令和坐标，定义了实际的图形路径。

6. 使用SVG的优势：
   - 文件大小通常较小。
   - 可以通过CSS或JavaScript动态修改。
   - 适合需要在不同设备和分辨率下保持清晰的场景。

总之，SVG确实是一种代码形式，它描述了如何绘制图形。浏览器和其他支持SVG的软件会解释这段代码并渲染出相应的图形。这种基于代码的图形描述方式使得SVG具有很高的灵活性和可扩展性。

[SVG website](https://www.svgrepo.com/vectors/home/)