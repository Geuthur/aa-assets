$(document).ready(() => {
    /* global tableAssets, RequestStatistics */
    const modalRequestOrder = $('#assets-single-request');
    const modalErrorMessage = $('#modal-error-message');

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

        $('#modal-button-confirm-single-request').on('click', () => {
            const form = modalRequestOrder.find('form');
            const amountField = form.find('input[name="amount"]');
            const amount = amountField.val();
            const csrfMiddlewareToken = form.find('input[name="csrfmiddlewaretoken"]').val();

            if (!amount) {
                modalErrorMessage.removeClass('d-none');
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
                        item_id: button.data('item-id'),
                        location_id: button.data('location-id'),
                        csrfmiddlewaretoken: csrfMiddlewareToken
                    }
                );

                posting.done(() => {
                    modalRequestOrder.modal('hide');
                    RequestStatistics.ajax.reload(); // Reload the request statistics table
                    tableAssets.ajax.reload(); // Reload the assets table
                }).fail((xhr, _, __) => {
                    const response = JSON.parse(xhr.responseText);
                    modalErrorMessage.text(response.message).removeClass('d-none'); // Show the error message
                    modalErrorMessage.addClass('l-shake'); // Add the shake class

                    // Remove the shake class after 2 seconds
                    setTimeout(() => {
                        modalErrorMessage.removeClass('l-shake');
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