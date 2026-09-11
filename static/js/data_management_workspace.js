document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
       SEARCH
       ===================================================== */

    const searchInput =
        document.getElementById("datasetSearch");

    const rows =
        document.querySelectorAll(".dataset-row");

    const searchEmpty =
        document.getElementById("searchEmpty");


    if (searchInput) {

        searchInput.addEventListener("input", function () {

            const query =
                this.value.trim().toLowerCase();

            let visibleRows = 0;


            rows.forEach(function (row) {

                const name =
                    row.dataset.name || "";

                const type =
                    row.dataset.type || "";


                const matches =
                    name.includes(query) ||
                    type.includes(query);


                row.style.display =
                    matches ? "" : "none";


                if (matches) {
                    visibleRows++;
                }

            });


            if (searchEmpty) {

                searchEmpty.style.display =
                    visibleRows === 0 && query
                        ? "block"
                        : "none";

            }

        });

    }



    /* =====================================================
       SELECT ALL
       ===================================================== */

    const selectAll =
        document.getElementById("selectAllDatasets");

    const checkboxes =
        document.querySelectorAll(
            ".dataset-checkbox"
        );

    const bulkToolbar =
        document.getElementById("bulkToolbar");

    const selectedCount =
        document.getElementById("selectedCount");


    function updateBulkToolbar() {

        const selected =
            document.querySelectorAll(
                ".dataset-checkbox:checked"
            ).length;


        if (selectedCount) {

            selectedCount.textContent =
                selected;

        }


        if (bulkToolbar) {

            bulkToolbar.classList.toggle(
                "visible",
                selected > 0
            );

        }

    }


    if (selectAll) {

        selectAll.addEventListener(
            "change",
            function () {

                checkboxes.forEach(
                    function (checkbox) {

                        checkbox.checked =
                            selectAll.checked;

                    }
                );


                updateBulkToolbar();

            }
        );

    }


    checkboxes.forEach(
        function (checkbox) {

            checkbox.addEventListener(
                "change",
                function () {

                    if (!this.checked &&
                        selectAll) {

                        selectAll.checked = false;

                    }


                    const allChecked =
                        checkboxes.length > 0 &&
                        Array.from(checkboxes)
                            .every(
                                item => item.checked
                            );


                    if (selectAll) {

                        selectAll.checked =
                            allChecked;

                    }


                    updateBulkToolbar();

                }
            );

        }
    );



    /* =====================================================
       ACTION DROPDOWNS
       ===================================================== */

    const dropdowns =
        document.querySelectorAll(
            ".action-dropdown"
        );


    dropdowns.forEach(
        function (dropdown) {

            const button =
                dropdown.querySelector(
                    ".action-more"
                );


            if (!button) return;


            button.addEventListener(
                "click",
                function (event) {

                    event.stopPropagation();


                    dropdowns.forEach(
                        function (other) {

                            if (other !== dropdown) {

                                other.classList.remove(
                                    "open"
                                );

                            }

                        }
                    );


                    dropdown.classList.toggle(
                        "open"
                    );

                }
            );

        }
    );


    document.addEventListener(
        "click",
        function () {

            dropdowns.forEach(
                function (dropdown) {

                    dropdown.classList.remove(
                        "open"
                    );

                }
            );

        }
    );



    /* =====================================================
       ROW ENTRANCE ANIMATION
       ===================================================== */

    rows.forEach(
        function (row, index) {

            row.style.opacity = "0";
            row.style.transform =
                "translateY(8px)";


            setTimeout(
                function () {

                    row.style.transition =
                        "opacity .4s ease, transform .4s ease";

                    row.style.opacity = "1";
                    row.style.transform =
                        "translateY(0)";

                },
                70 + (index * 45)
            );

        }
    );

});