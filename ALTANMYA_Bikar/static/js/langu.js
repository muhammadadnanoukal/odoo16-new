// Get references to the two links
const link1 = document.querySelector('.js_change_lang.active');
const link2 = document.querySelector('.js_change_lang:not(.active)');
var separator = document.querySelector('span.list-inline-item');



// Hide link1 initially
link1.style.display = 'none';
separator.style.display = 'none';

// Add click event listener to link2
link2.addEventListener('click', function() {
  // Hide link2
  link2.style.display = 'none';
  // Show link1
  link1.style.display = 'inline-block';
  // Make link1 active
  link1.classList.add('active');
  // Make link2 inactive
  link2.classList.remove('active');
});

// Add click event listener to link1
link1.addEventListener('click', function() {
  // Hide link1
  link1.style.display = 'none';
  // Show link2
  link2.style.display = 'inline-block';
  // Make link2 active
  link2.classList.add('active');
  // Make link1 inactive
  link1.classList.remove('active');
});