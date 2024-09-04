var markRequestCancelledText = requestSettings.markRequestCancelledText;
var markRequestCompletedText = requestSettings.markRequestCompletedText;
var markRequestOpenText = requestSettings.markRequestOpenText;
var manage_requests = requestSettings.manage_requests;

var csrfToken = requestSettings.csrfToken;
var urlRequests, urlMyRequests;

document.addEventListener('DOMContentLoaded', function () {
    urlRequests = '/assets/api/requests/';
    urlMyRequests = '/assets/api/requests/myrequests/';
    // Initialisieren Sie die DataTable für assets
    requests = initializeRequests('#requests', urlRequests);
    myrequests = initializeRequests('#my-requests', urlMyRequests);
    var confirmModal = document.getElementById('confirmRequestModal');
    var confirmRequest = document.getElementById('confirm-request');
    var finalizeActionButton = document.getElementById('finalizeActionButton');

    confirmModal.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        var confirmText = button.getAttribute('data-confirm-text');
        var formId = button.getAttribute('data-form-id');

        confirmRequest.textContent = confirmText;

        finalizeActionButton.onclick = function () {
            document.getElementById(formId).submit();
            var modal = bootstrap.Modal.getInstance(confirmModal);
            modal.hide();
        };
    });
});

function cancelRequestUrl(id) {
    return requestSettings.cancelRequestUrl.replace("1337", id);
}
function completeRequestUrl(id) {
    return requestSettings.completeRequestUrl.replace("1337", id);
}
function openRequestUrl(id) {
    return requestSettings.openRequestUrl.replace("1337", id);
}

function initializeRequests(tableId, url) {
    return $(tableId).DataTable({
        'ajax': {
            'url': url,
            'dataSrc': function(json) {
                // Store the data in a global variable
                return json;
            }
        },
        'columns': [
            {
                'data': 'order',
                'render': function(data, type, row) {
                    return '<button type="button" class="btn btn-info btn-sm btn-square" onclick=\'showOrderDetails(`' + data + '`)\'><span class="fas fa-info"></span></button>';
                }
            },
            {
                'data': 'requestor',
                'render': function(data, type, row) {
                    return data;
                }
            },
            {
                'data': 'status',
                'render': function(data, type, row) {
                    return data;
                }
            },
            {
                'data': 'created',
                'render': function(data, type, row) {
                    return moment(data).format('L LT');
                }
            },
            {
                className: "text-end",
                'data': 'id',
            },
        ],
        'order': [[3, 'desc']],
        'pageLength': 25,
        'autoWidth': false,
        'columnDefs': [
            { 'sortable': false, 'targets': [0, 4] },
            {
                render: function (data, type, row) {
                if (type === "display") {
                    var buttons = '';
                    if (row.action === "OP") {
                        buttons +=
                            '<form class="d-inline" method="post" action="' + cancelRequestUrl(data) + '" id="cancelForm' + data.id + '">' +
                            csrfToken +
                            '<button type="button" class="btn btn-danger btn-sm btn-square" aria-label="' + markRequestCancelledText + '" title="' + markRequestCancelledText + '" data-bs-toggle="modal" data-bs-target="#confirmRequestModal" data-confirm-text="' + markRequestCancelledText + '" data-form-id="cancelForm' + data.id + '"><span class="fas fa-trash"></span></button></form>';
                        if (manage_requests === "true") {
                            buttons +=
                                '<form class="d-inline" method="post" action="' + completeRequestUrl(data) + '" id="completeForm' + data.id + '">' +
                                csrfToken +
                                '<button type="button" class="btn btn-success btn-sm btn-square" aria-label="' + markRequestCompletedText + '" title="' + markRequestCompletedText + '" data-bs-toggle="modal" data-bs-target="#confirmRequestModal" data-confirm-text="' + markRequestCompletedText + '" data-form-id="completeForm' + data.id + '"><span class="fas fa-clipboard-check"></span></button></form>';
                        }
                        return buttons;
                    } else if (row.action === "CL") {
                        buttons +=
                            '<form class="d-inline" method="post" action="' + openRequestUrl(data) + '" id="openForm' + data.id + '">' +
                            csrfToken +
                            '<button type="button" class="btn btn-warning btn-sm btn-square" aria-label="' + markRequestOpenText + '" title="' + markRequestOpenText + '" data-bs-toggle="modal" data-bs-target="#confirmRequestModal" data-confirm-text="' + markRequestOpenText + '" data-form-id="openForm' + data.id + '"><span class="fas fa-undo"></span></button></form>';
                        return buttons;
                    } else {
                        return "";
                    }
                }

                return data;
            },
            targets: [4],
        },
        ],
    });
}

function showOrderDetails(data) {
    // Parse the JSON string
    var jsonData = JSON.parse(data);

    // Initialize an empty HTML string
    var html = '';

    // Iterate through each entry in the JSON data
    jsonData.forEach(function(entry) {
        // Extract the required fields
        var item_id = entry.item_id;
        var name = entry.name;
        var quantity = Number(entry.quantity);

        // Append the formatted data to the HTML string
        html += '<div class="d-flex justify-content-between align-items-center">';
        html += '<img class="card-img-zoom" src="https://imageserver.eveonline.com/types/' + item_id + '/icon/?size=32" height="32" width="32"/>';
        html += '<span>' + name + ':</span> <span class="text-end">' + quantity.toLocaleString() + ' {% translate "pieces" %}</span>';
        html += '</div><br>';
    });

    // Set the HTML content of the modal body
    document.getElementById('orderModalBody').innerHTML = html;

    // Show the modal
    var orderModal = new bootstrap.Modal(document.getElementById('orderModal'));
    orderModal.show();
}