$(document).ready(() => {
    /* global tablePayments */
    /* global taxsystemsettings */
    const modalRequestOrder = $('single-request');
    const modalRequestOrderError = modalRequestOrder.find('#modal-error-field');
    //const previousUndoModal = $('#modalViewPaymentsContainer');

    // Undo Request Modal
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

        $('#modal-button-cancel-single-request').on('click', () => {
            const form = modalRequestOrder.find('form');
            const amountField = form.find('input[name="amount"]');
            const amount = amountField.val();
            const csrfMiddlewareToken = form.find('input[name="csrfmiddlewaretoken"]').val();

            if (amount === '') {
                modalRequestOrderError.removeClass('d-none');
                amountField.addClass('is-invalid');

                // Add shake class to the error field
                modalRequestOrderError.addClass('ts-shake');

                // Remove the shake class after 3 seconds
                setTimeout(() => {
                    modalRequestOrderError.removeClass('ts-shake');
                }, 2000);
            } else {
                const posting = $.post(
                    url,
                    {
                        amount: amount,
                        csrfmiddlewaretoken: csrfMiddlewareToken
                    }
                );

                posting.done((data) => {
                    if (data.success === true) {
                        modalRequestOrder.modal('hide');
                    } else {
                        console.log(data.message);
                        // Show the error message
                        const errorMessage = data.message;
                        $(errorMessage).insertAfter(amountField);
                    }
                }).fail((xhr, _, __) => {
                    const response = JSON.parse(xhr.responseText);
                    const errorMessage = $('<div class="alert alert-danger"></div>').text(response.message);
                    form.append(errorMessage);
                });
            }
        });
    }).on('hide.bs.modal', () => {
        modalRequestOrder.find('input[name="amount"]').val('');
        modalRequestOrder.find('input[name="amount"]').removeClass('is-invalid');
        modalRequestOrder.find('.alert-danger').remove();
        modalRequestOrderError.addClass('d-none');
        $('#modal-button-cancel-single-request').unbind('click');
    });
});
