/* Knowledge Corpus Manager - Client-side interactions */

// Toggle directory expansion in browse view
document.addEventListener('click', function (e) {
    const dirRow = e.target.closest('.dir-row');
    if (!dirRow) return;

    // Find the associated subdir container
    const parent = dirRow.closest('.list-group-item');
    if (!parent) return;

    const subdirContainer = parent.querySelector('.subdir-contents');
    if (!subdirContainer) return;

    // Toggle visibility
    const isVisible = subdirContainer.style.display !== 'none';
    subdirContainer.style.display = isVisible ? 'none' : 'block';

    // Toggle arrow icon
    dirRow.classList.toggle('expanded', !isVisible);
});
