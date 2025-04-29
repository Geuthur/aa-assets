$(document).ready(() => {
    /* global PlanetaryTable */
    const modalRequestOrder = $('#assets-confirm-request');
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

        $('#modal-button-confirm-request').on('click', () => {
            const form = modalRequestOrder.find('form');
            const csrfMiddlewareToken = form.find('input[name="csrfmiddlewaretoken"]').val();
            const posting = $.post(
                url,
                {
                    request_pk: button.data('request-pk'),
                    csrfmiddlewaretoken: csrfMiddlewareToken
                }
            );

            posting.done(() => {
                modalRequestOrder.modal('hide');
            }).fail((xhr, _, __) => {
                const response = JSON.parse(xhr.responseText);
                modalErrorMessage.text(response.message).removeClass('d-none'); // Show the error message
                modalErrorMessage.addClass('l-shake'); // Add the shake class

                // Remove the shake class after 2 seconds
                setTimeout(() => {
                    modalErrorMessage.removeClass('l-shake');
                }, 2000);
            });
        });
    }).on('hide.bs.modal', () => {
        modalRequestOrder.find('.alert-danger').remove();
        modalRequestOrder.find('input[name="amount"]').val('');
        modalRequestOrder.find('input[name="amount"]').removeClass('is-invalid');
        $('#modal-button-confirm-request').unbind('click');
        modalErrorMessage.addClass('d-none');
        modalErrorMessage.val('');
    });
});