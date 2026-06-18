document.addEventListener('DOMContentLoaded', function () {
    document.body.addEventListener('click', function (e) {
        if (e.target.classList.contains('copy-btn')) {
            const button = e.target;
            const targetId = button.getAttribute('data-clipboard-target');
            const targetElement = document.querySelector(targetId);
            const textToCopy = targetElement.querySelector('pre').innerText;
            const originalText = button.getAttribute('data-original-text') || button.innerText;

            if (!button.getAttribute('data-original-text')) {
                button.setAttribute('data-original-text', originalText);
            }

            navigator.clipboard.writeText(textToCopy).then(() => {
                button.innerText = 'Copied!';
                setTimeout(() => {
                    button.innerText = originalText;
                }, 2000);
            });
        }

        if (e.target.classList.contains('download-btn')) {
            const button = e.target;
            const targetId = button.getAttribute('data-target');
            const lang = button.getAttribute('data-lang');
            const targetElement = document.querySelector(targetId);
            const codeContent = targetElement.querySelector('pre').innerText;

            let filename = 'code.txt';
            if (lang === 'python') filename = 'script.py';
            else if (lang === 'java') filename = 'Main.java';
            else if (lang === 'javascript' || lang === 'js') filename = 'script.js';
            else if (lang === 'html') filename = 'page.html';
            else if (lang === 'css') filename = 'styles.css';
            else if (lang === 'cpp') filename = 'program.cpp';
            else if (lang === 'go') filename = 'main.go';

            const blob = new Blob([codeContent], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    });
});
