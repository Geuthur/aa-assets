var orderData;

function initializeRequests(tableId, url) {
    return $(tableId).DataTable({
        'ajax': {
            'url': url,
            'dataSrc': function(json) {
                // Store the data in a global variable
                orderData = json;
                return json;
            }
        },
        'columns': [
            {
                'data': 'id',
                'render': function(data, type, row) {
                    return data;
                }
            },
            {
                'data': 'order',
                'render': function(data, type, row) {
                    return '<button type="button" class="btn btn-info" onclick=\'showOrderDetails(`' + data + '`)\'><span class="fas fa-info"></span></button>';
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
                    // eslint-disable-next-line no-undef
                    return moment(data).format('L LT');
                }
            },
            {
                'data': null,
                'render': function(data, type, row) {
                    return '';
                }
            }
        ],
        'order': [[4, 'desc']],
        'pageLength': 25,
        'autoWidth': false,
        'columnDefs': [
            { 'sortable': false, 'targets': [0, 5] },
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
    // eslint-disable-next-line no-undef
    var orderModal = new bootstrap.Modal(document.getElementById('orderModal'));
    orderModal.show();
}

document.addEventListener('DOMContentLoaded', function () {

    var urlRequests = '/assets/api/requests/';
    // Initialisieren Sie die DataTable für assets
    var assets = initializeRequests('#requests', urlRequests);
});
