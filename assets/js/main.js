(function(){
  function isKeyboardActivate(e){
    return e.key === 'Enter' || e.key === ' ';
  }

  const triggers = document.querySelectorAll('.reveal-trigger');
  triggers.forEach((t) => {
    t.setAttribute('role','button');
    t.setAttribute('tabindex','0');

    const block = t.closest('.reveal-block');
    if(!block) return;

    // Default aria state
    t.setAttribute('aria-expanded', block.classList.contains('open') ? 'true' : 'false');

    function toggle(){
      const open = block.classList.toggle('open');
      t.setAttribute('aria-expanded', open ? 'true' : 'false');
    }

    t.addEventListener('click', (e) => {
      // On desktop, hover already works; click gives a "sticky open" option.
      e.preventDefault();
      toggle();
    });

    t.addEventListener('keydown', (e) => {
      if(isKeyboardActivate(e)){
        e.preventDefault();
        toggle();
      }
    });
  });
})();
