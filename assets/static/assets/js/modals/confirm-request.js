$(document).ready(() => {
    /* global tableAssets, loadRequestStatistics */
    const modalRequestConfirm = $('#assets-confirm-request');
    const modalConfirmErrorMessage = modalRequestConfirm.find('#modal-error-message');

    // Approve Request Modal
    modalRequestConfirm.on('show.bs.modal', (event) => {
        const button = $(event.relatedTarget);
        const url = button.data('action');

        // Extract the title from the button
        const modalTitle = button.data('title');
        const modalTitleDiv = modalRequestConfirm.find('#modal-title');
        modalTitleDiv.html(modalTitle);

        // Extract the text from the button
        const modalText = button.data('text');
        const modalDiv = modalRequestConfirm.find('#modal-request-text');
        modalDiv.html(modalText);

        $('#modal-button-confirm-request').on('click', () => {
            const form = modalRequestConfirm.find('form');
            const csrfMiddlewareToken = form.find('input[name="csrfmiddlewaretoken"]').val();
            const posting = $.post(
                url,
                {
                    request_pk: button.data('request-pk'),
                    csrfmiddlewaretoken: csrfMiddlewareToken
                }
            );

            posting.done(() => {
                modalRequestConfirm.modal('hide');
                loadRequestStatistics(); // Reload the request statistics
                const tableAssets = $('#assets').DataTable();
                const tableMyRequest = $('#my-requests').DataTable();
                const tableRequest = $('#requests').DataTable();
                tableAssets.ajax.reload(); // Reload the assets table
                tableMyRequest.ajax.reload(); // Reload the my requests table
                tableRequest.ajax.reload(); // Reload the requests table
            }).fail((xhr, _, __) => {
                const response = JSON.parse(xhr.responseText);
                modalConfirmErrorMessage.text(response.message).removeClass('d-none'); // Show the error message
                modalConfirmErrorMessage.addClass('ts-shake'); // Add the shake class

                // Remove the shake class after 2 seconds
                setTimeout(() => {
                    modalConfirmErrorMessage.removeClass('ts-shake');
                }, 2000);
            });
        });
    }).on('hide.bs.modal', () => {
        modalRequestConfirm.find('.alert-danger').remove();
        modalRequestConfirm.find('input[name="amount"]').val('');
        modalRequestConfirm.find('input[name="amount"]').removeClass('is-invalid');
        $('#modal-button-confirm-request').unbind('click');
        modalConfirmErrorMessage.addClass('d-none');
        modalConfirmErrorMessage.val('');
    });
});
