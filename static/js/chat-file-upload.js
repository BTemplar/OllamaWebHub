const fileInputEl = document.getElementById('fileInput');
if (fileInputEl) {
    fileInputEl.addEventListener('change', function () {
        const icon = this.closest('.file-upload').querySelector('i');
        if (this.files.length > 0) {
            icon.parentElement.classList.add('file-selected');
        } else {
            icon.parentElement.classList.remove('file-selected');
        }
    });
}
