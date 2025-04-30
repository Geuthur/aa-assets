$(document).ready(() => {
    /* global tableAssets, loadRequestStatistics */
    const modalRequestOrder = $('#assets-multi-request');
    const modalErrorMessage = modalRequestOrder.find('#modal-error-message');
    const modalErrorRequiredText = modalErrorMessage.text();

    // Approve Request Modal
    modalRequestOrder.on('show.bs.modal', (event) => {
        const button = $(event.relatedTarget);
        const url = button.data('action');

        // Extract the title from the button
        const modalTitle = button.data('title');
        const modalTitleDiv = modalRequestOrder.find('#modal-title');
        modalTitleDiv.html(modalTitle);

        // Extract the text from the button
        const modalText = button.data('text');
        const modalDiv = modalRequestOrder.find('#modal-request-text');
        modalDiv.html(modalText);

        const form = modalRequestOrder.find('form');
        const amountField = form.find('input[name="amount"]');
        const itemQuantity = button.data('item-quantity');

        $('#modal-button-buy-multi-request').on('click', () => {
            amountField.val(itemQuantity); // Set the amount to the maximum quantity
        });

        $('#modal-button-confirm-multi-request').on('click', () => {
            const form = modalRequestOrder.find('form');
            const csrfMiddlewareToken = form.find('input[name="csrfmiddlewaretoken"]').val();

            // Sammle alle Felder mit Namen, die mit "amount_" beginnen
            const formData = {};
            form.find('input[name^="amount_"]').each((_, input) => {
                const itemQuantity = $(input).data('quantity');

                // Automatically correct the input value if it exceeds the max value
                $(input).on('input', () => {
                    const currentValue = parseInt($(input).val(), 10);
                    if (currentValue > itemQuantity) {
                        amountField.val(itemQuantity); // Set to max value
                    }
                });

                const fieldName = $(input).attr('name');
                const fieldValue = $(input).val();

                // Nur Felder mit einem Wert hinzufügen
                if (fieldValue && parseInt(fieldValue, 10) > 0) {
                    formData[fieldName] = fieldValue;
                }
            });

            // Füge das CSRF-Token zur Anfrage hinzu
            formData['csrfmiddlewaretoken'] = csrfMiddlewareToken;

            // Asset-PK aus dem Button-Data-Attribut hinzufügen
            formData['asset_pk'] = button.data('asset-pk');

            // Sende die Daten per POST
            const posting = $.post(url, formData);

            posting.done(() => {
                modalRequestOrder.modal('hide');
                loadRequestStatistics(); // Reload the request statistics
                const tableAssets = $('#assets').DataTable();
                const tableMyRequest = $('#my-requests').DataTable();
                const tableRequest = $('#requests').DataTable();
                tableAssets.ajax.reload(); // Reload the assets table
                tableMyRequest.ajax.reload(); // Reload the my requests table
                tableRequest.ajax.reload(); // Reload the requests table
            }).fail((xhr, _, __) => {
                const response = JSON.parse(xhr.responseText);
                modalErrorMessage.text(response.message).removeClass('d-none'); // Show the error message
                // Add shake class to the error field
                modalErrorMessage.addClass('ts-shake');

                // Remove the shake class after 3 seconds
                setTimeout(() => {
                    modalErrorMessage.removeClass('ts-shake');
                }, 2000);
            });
        });
    }).on('hide.bs.modal', () => {
        modalRequestOrder.find('.alert-danger').remove();
        modalRequestOrder.find('input[name="amount"]').val('');
        modalRequestOrder.find('input[name="amount"]').removeClass('is-invalid');
        $('#modal-button-confirm-multi-request').unbind('click');
        modalErrorMessage.addClass('d-none');
        modalErrorMessage.val('');
    });
});
