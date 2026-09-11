document.addEventListener("DOMContentLoaded", function () {

    const fileInput =
        document.querySelector(
            '.smart-file-dropzone input[type="file"]'
        );

    const fileName =
        document.getElementById(
            "selectedFileName"
        );

    const submitButton =
        document.getElementById(
            "uploadSubmitButton"
        );


    if (fileInput && fileName) {

        fileInput.addEventListener(
            "change",
            function () {

                if (fileInput.files.length > 0) {

                    const file =
                        fileInput.files[0];

                    fileName.textContent =
                        "Selected: " + file.name;

                } else {

                    fileName.textContent = "";

                }

            }
        );

    }


    if (submitButton) {

        submitButton.closest("form")
            ?.addEventListener(
                "submit",
                function () {

                    submitButton.disabled = true;

                    submitButton.style.opacity = "0.7";

                    submitButton.querySelector(
                        "span:first-child"
                    ).textContent =
                        "Uploading...";

                }
            );

    }

});