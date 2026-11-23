(function () {
  function hideLoader() {
    var el = document.getElementById('initial-loader')
    if (!el) return
    el.classList.add('fade-out')
    setTimeout(function () {
      if (el && el.parentNode) el.parentNode.removeChild(el)
    }, 300)
  }
  window.addEventListener('app-ready', hideLoader)
  var observer = new MutationObserver(function () {
    var root = document.getElementById('root')
    if (root && root.children.length > 0) hideLoader()
  })
  observer.observe(document.getElementById('root'), { childList: true, subtree: false })
  setTimeout(hideLoader, 8000)
})()
