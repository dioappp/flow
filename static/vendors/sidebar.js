document.addEventListener('DOMContentLoaded', function () {
  // Check the sidebar state on page load
  if (localStorage.getItem('sidebarState') === 'hidden') {
      document.querySelector('body').classList.add('pc-sidebar-hide');
  } else {
      document.querySelector('body').classList.remove('pc-sidebar-hide');
  }

  // Add event listener to update localStorage when sidebar state changes
  var observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
          if (mutation.attributeName === 'class') {
              var body = document.querySelector('body');
              if (body.classList.contains('pc-sidebar-hide')) {
                  localStorage.setItem('sidebarState', 'hidden');
              } else {
                  localStorage.setItem('sidebarState', 'shown');
              }
          }
      });
  });

  // Observe changes to the body's class attribute
  observer.observe(document.querySelector('body'), {
      attributes: true
  });
});