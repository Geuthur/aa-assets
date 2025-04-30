$(document).ready(() => {
    /* global tableAssets, loadRequestStatistics */
    const modalRequestOrder = $('#assets-single-request');
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

        // Set the max attribute for the amount field
        amountField.attr('max', itemQuantity);

        // Automatically correct the input value if it exceeds the max value
        amountField.on('input', () => {
            const currentValue = parseInt(amountField.val(), 10);
            if (currentValue > itemQuantity) {
                amountField.val(itemQuantity); // Set to max value
            }
        });

        $('#modal-button-buy-single-request').on('click', () => {
            amountField.val(itemQuantity); // Set the amount to the maximum quantity
        });

        $('#modal-button-confirm-single-request').on('click', () => {
            const amount = amountField.val();
            const csrfMiddlewareToken = form.find('input[name="csrfmiddlewaretoken"]').val();

            if (!amount || amount > itemQuantity) {
                modalErrorMessage.text(modalErrorRequiredText).removeClass('d-none');
                amountField.addClass('is-invalid');

                // Add shake class to the error field
                modalErrorMessage.addClass('ts-shake');

                // Remove the shake class after 3 seconds
                setTimeout(() => {
                    modalErrorMessage.removeClass('ts-shake');
                }, 2000);
            } else {
                const posting = $.post(
                    url,
                    {
                        amount: amount,
                        asset_pk: button.data('asset-pk'),
                        csrfmiddlewaretoken: csrfMiddlewareToken
                    }
                );

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
            }
        });
    }).on('hide.bs.modal', () => {
        modalRequestOrder.find('.alert-danger').remove();
        modalRequestOrder.find('input[name="amount"]').val('');
        modalRequestOrder.find('input[name="amount"]').removeClass('is-invalid');
        $('#modal-button-confirm-single-request').unbind('click');
        modalErrorMessage.addClass('d-none');
        modalErrorMessage.val('');
    });
});
