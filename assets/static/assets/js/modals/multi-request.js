$(document).ready(() => {
    function handleError(xhr) {
        const response = JSON.parse(xhr.responseText);
        modalErrorMessage.text(response.message).removeClass('d-none'); // Show the error message
        modalErrorMessage.addClass('ts-shake'); // Add shake class to the error field

        // Remove the shake class after 3 seconds
        setTimeout(() => {
            modalErrorMessage.removeClass('ts-shake');
        }, 2000);

        if (xhr.status === 409) {
            modalErrorMessage.removeClass('bg-danger').addClass('bg-warning'); // Change to warning color
            setTimeout(() => {
                modalErrorMessage.removeClass('bg-warning').addClass('bg-danger'); // Change back to danger color
                modalRequestOrder.modal('hide');
                reloadTables(); // Tabellen neu laden
            }, 5000);
        }
    }

    // Funktion zum Neuladen der Tabellen
    function reloadTables() {
        loadRequestStatistics(); // Reload the request statistics
        const tableAssets = $('#assets').DataTable();
        const tableMyRequest = $('#my-requests').DataTable();
        const tableRequest = $('#requests').DataTable();
        tableAssets.ajax.reload(); // Reload the assets table
        tableMyRequest.ajax.reload(); // Reload the my requests table
        tableRequest.ajax.reload(); // Reload the requests table
    }

    /* global tableAssets, loadRequestStatistics */
    const modalRequestOrder = $('#assets-multi-request');
    const modalErrorMessage = modalRequestOrder.find('#modal-error-message');
    const modalErrorRequiredText = modalErrorMessage.text();
    const modalForm = modalRequestOrder.find('form');

    // Input Fields
    const inputFields = {};
    modalForm.find('input[name^="item_id_"]').each(function () {
        const fieldName = $(this).attr('name');
        inputFields[fieldName] = $(this);
    });

    // Approve Request Modal
    modalRequestOrder.on('show.bs.modal', (event) => {
        const button = $(event.relatedTarget);

        // Form Data
        const url = button.data('action');
        // Extract the CSRF token from the form
        const csrfMiddlewareToken = modalForm.find('input[name="csrfmiddlewaretoken"]').val();
        // Extract the title from the button
        const modalTitle = button.data('title');

        // Set the title in the modal
        const modalTitleDiv = modalRequestOrder.find('#modal-title');
        modalTitleDiv.html(modalTitle);

        // Extract the text from the button
        const modalText = button.data('text');
        const modalDiv = modalRequestOrder.find('#modal-request-text');
        modalDiv.html(modalText);

        // Limit the input to max quantity
        Object.entries(inputFields).forEach(([fieldName, inputField]) => {
            const maxQuantity = parseInt(inputField.data('quantity'), 10); // Maximalwert des Feldes
            inputField.on('input', () => {
                const currentValue = parseInt(inputField.val(), 10);
                if (currentValue > maxQuantity) {
                    inputField.val(maxQuantity); // Auf Maximalwert setzen
                }
            });
        });

        $('#modal-button-confirm-multi-request').on('click', () => {
            let cleaned_data = {};

            // Set Form Data
            Object.entries(inputFields).forEach(([fieldName, inputField]) => {
                const value = parseInt(inputField.val(), 10);
                if (!isNaN(value) && value > 0) {
                    cleaned_data[fieldName] = value;
                }
            });

            if (Object.keys(cleaned_data).length === 0) {
                modalErrorMessage.text(modalErrorRequiredText).removeClass('d-none'); // Show the error message
                // Add shake class to the error field
                modalErrorMessage.addClass('ts-shake');

                // Remove the shake class after 3 seconds
                setTimeout(() => {
                    modalErrorMessage.removeClass('ts-shake');
                }, 2000);
            } else {
                cleaned_data['csrfmiddlewaretoken'] = csrfMiddlewareToken; // Füge das CSRF-Token hinzu
                const posting = $.post(
                    url,
                    cleaned_data,
                );

                posting.done(() => {
                    modalRequestOrder.modal('hide');
                    reloadTables(); // Tabellen neu laden

                    // Update maxQuantity and hide inputs if necessary
                    Object.entries(inputFields).forEach(([fieldName, inputField]) => {
                        const maxQuantity = parseInt(inputField.data('quantity'), 10); // Maximalwert des Feldes
                        const currentValue = cleaned_data[fieldName] || 0; // Aktueller Wert des Feldes

                        if (currentValue >= maxQuantity) {
                            // Hide the input field if the current value is greater than or equal to max quantity
                            inputField.closest('.form-group').addClass('d-none');
                        }
                        // Update the data-quantity attribute for remaining quantity
                        const remainingQuantity = maxQuantity - currentValue;
                        // Update the data-quantity attribute
                        inputField.data('quantity', remainingQuantity);
                        // Reset the input field value
                        inputField.val();
                    });
                }).fail((xhr, _, __) => {
                    handleError(xhr); // Fehlerbehandlung
                });
            }
        });
    }).on('hide.bs.modal', () => {
        modalRequestOrder.find('.alert-danger').remove();
        Object.entries(inputFields).forEach(([fieldName, inputField]) => {
            inputField.val('');
        });
        $('#modal-button-confirm-multi-request').unbind('click');
        modalErrorMessage.addClass('d-none');
        modalErrorMessage.val('');
    });
});
