document.addEventListener('DOMContentLoaded', (event) => {
    const formContainer = document.getElementById('fields');
    let formData = {};

    // Function to store form data
    function storeFormData() {
        formContainer.querySelectorAll('input, select, textarea').forEach((input) => {
            formData[input.name] = input.value;
        });
    }

    // Function to restore form data
    function restoreFormData() {
        formContainer.querySelectorAll('input, select, textarea').forEach((input) => {
            if (formData.hasOwnProperty(input.name)) {
                input.value = formData[input.name];
            }
        });
    }

    if (formContainer !== null) {
        // Stored initial values, when editing an existing entry
        storeFormData();

        // Listen for changes on form inputs to store data
        formContainer.addEventListener('input', storeFormData);
    }

    // Listen for htmx afterSwap to restore data
    document.body.addEventListener('htmx:afterSwap', (event) => {
        if (event.detail.target === formContainer) {
            restoreFormData();
        }
    });

    // function for speaking pronunciations
    const rtElement = document.querySelector('[data-audio-url]');
    if (rtElement) {
        rtElement.addEventListener('click', (event) => {
            event.preventDefault();

            const audioUrls = JSON.parse(rtElement.getAttribute('data-audio-url'));
            let currentIndex = 0;

            const playNextAudio = () => {
                if (currentIndex < audioUrls.length) {
                    const audio = new Audio(audioUrls[currentIndex]);
                    audio.addEventListener('ended', () => {
                        currentIndex++;
                        playNextAudio();
                    });
                    audio.play();
                }
            };

            playNextAudio();
        });
    }
});
