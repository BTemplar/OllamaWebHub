document.addEventListener('DOMContentLoaded', () => {
    const multimodalModels = (document.getElementById('multimodal-models')?.dataset.models || '')
        .split(';')
        .map((item) => item.trim().toLowerCase())
        .filter(Boolean);

    const thinkModels = (document.getElementById('reasoning-models')?.dataset.models || '')
        .split(';')
        .map((item) => item.trim().toLowerCase())
        .filter(Boolean);

    function bindRange(inputId, displayId) {
        const input = document.getElementById(inputId);
        const display = document.getElementById(displayId);
        if (!input || !display) return;
        display.textContent = input.value;
        input.addEventListener('input', () => {
            display.textContent = input.value;
        });
    }

    function initChatForm(prefix) {
        const modelSelect = document.getElementById(`${prefix}ModelSelect`);
        const multimodalCheckbox = document.getElementById(`${prefix}MultimodalCheckbox`);
        const thinkCheckbox = document.getElementById(`${prefix}ThinkCheckbox`);
        const reasoningCheckbox = document.getElementById(`${prefix}ReasoningCheckbox`);

        if (!modelSelect) return;

        function getSelectedModel() {
            return modelSelect.value.split(':')[0].trim().toLowerCase();
        }

        function updateMultimodalCheckboxState() {
            if (!multimodalCheckbox) return;
            const isAvailable = multimodalModels.includes(getSelectedModel());
            multimodalCheckbox.disabled = !isAvailable;
            if (!isAvailable) multimodalCheckbox.checked = false;
        }

        function updateThinkCheckboxState() {
            if (!thinkCheckbox) return;
            const isAvailable = thinkModels.includes(getSelectedModel());
            thinkCheckbox.disabled = !isAvailable;
            if (!isAvailable) thinkCheckbox.checked = false;
        }

        function updateReasoningCheckboxState() {
            if (!reasoningCheckbox || !thinkCheckbox) return;
            reasoningCheckbox.disabled = !thinkCheckbox.checked;
            if (!thinkCheckbox.checked) reasoningCheckbox.checked = false;
        }

        function refreshModelOptions() {
            updateMultimodalCheckboxState();
            updateThinkCheckboxState();
            updateReasoningCheckboxState();
        }

        modelSelect.addEventListener('change', refreshModelOptions);
        thinkCheckbox?.addEventListener('change', updateReasoningCheckboxState);
        refreshModelOptions();
    }

    bindRange('newTemperature', 'newRangeValue');
    bindRange('newNumCtx', 'newNumCtxValue');
    bindRange('editTemperature', 'editRangeValue');
    bindRange('editNumCtx', 'editNumCtxValue');

    initChatForm('new');
    initChatForm('edit');
});
