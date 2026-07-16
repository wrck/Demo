/**
 * 组件加载器 - 通过 fetch 动态加载组件 HTML
 * 支持 CSS 和 JS 的提取与执行
 */
var ComponentLoader = {
  loaded: {},

  load: function (componentPath, containerId, callback) {
    var container = document.getElementById(containerId);
    if (!container) return;

    // 已加载则跳过
    if (this.loaded[componentPath]) {
      if (callback) callback();
      return;
    }

    container.innerHTML =
      '<div style="padding:40px;text-align:center;color:#909399;">加载中...</div>';

    fetch(componentPath)
      .then(function (response) {
        return response.text();
      })
      .then(function (html) {
        container.innerHTML = '';

        // 解析 HTML，分离 style/script/body
        var tmp = document.createElement('div');
        tmp.innerHTML = html;

        // 注入样式
        var styles = tmp.querySelectorAll('style');
        for (var i = 0; i < styles.length; i++) {
          var style = styles[i];
          var clone = document.createElement('style');
          clone.textContent = style.textContent;
          // 添加 data-source 标记避免重复
          clone.setAttribute('data-component', componentPath);
          if (
            !document.querySelector(
              'style[data-component="' + componentPath + '"]'
            )
          ) {
            document.head.appendChild(clone);
          }
        }

        // 注入 body 内容
        var body = tmp.querySelector('.component-body');
        if (body) {
          container.innerHTML = body.innerHTML;
        } else {
          container.innerHTML = html;
        }

        // 执行脚本
        var scripts = tmp.querySelectorAll('script');
        for (var j = 0; j < scripts.length; j++) {
          var script = scripts[j];
          var newScript = document.createElement('script');
          if (script.src) {
            newScript.src = script.src;
          } else {
            newScript.textContent = script.textContent;
          }
          container.appendChild(newScript);
        }

        ComponentLoader.loaded[componentPath] = true;
        if (callback) callback();
      })
      .catch(function (err) {
        container.innerHTML =
          '<div style="padding:40px;text-align:center;color:#F56C6C;">组件加载失败: ' +
          err.message +
          '</div>';
      });
  }
};
