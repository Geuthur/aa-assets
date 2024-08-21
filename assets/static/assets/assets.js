var urlAssets;
var assets;
var action;

function initializeDataTable(tableId, url) {
    return $(tableId).DataTable({
        'ajax': {
            'url': url,
            'dataSrc': function(json) {
                return json;
            }
        },
        'columns': [
            {
                'data': 'item_id',
                'render': function(data, type, row) {
                    return '<img class="card-img-zoom" src="https://imageserver.eveonline.com/types/' + data + '/icon/?size=64" height="64" width="64"/>';
                }
            },
            {
                'data': 'name',
                'render': function(data, type, row) {
                    return data;
                }
            },
            {
                'data': 'quantity',
                'render': function (data, type, row) {
                    return data;
                }
            },
            {
                'data': 'location',
                'render': function (data, type, row) {
                    return data;
                }
            },
            {
                'data': 'price',
                'render': function (data, type, row) {
                    // Rückgabe des formatierten Strings mit Farbe und Einheit
                    if (type === 'display') {
                        if (!isNaN(data) && typeof data === 'number') {
                            return data.toLocaleString() + ' ISK';
                        }
                    }
                    return data;
                }
            },
            {
                'data': null,
                'render': function(data, type, row) {
                    return '<button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#buyModal" data-action="single" data-item-id="' + row.item_id + '" data-item-name="' + row.name + '" data-item-quantity="' + row.quantity + '">{% translate "Buy" %}</button>';
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

document.addEventListener('DOMContentLoaded', function () {
    urlAssets = '/assets/api/assets/filter/corpsag5/';
    // Initialisieren Sie die DataTable für assets
    assets = initializeDataTable('#assets', urlAssets);

    // Add event listener to the Buy button in the buy modal
    document.getElementById('confirmBuyButton').addEventListener('click', function(event) {
        event.preventDefault();
        if (validateForm()) {
            $('#buyModal').modal('hide');
            $('#confirmModal').modal('show');
        }
    });

    // Add event listener to the Confirm button in the confirmation modal
    document.getElementById('finalizeBuyButton').addEventListener('click', function(event) {
        event.preventDefault();
        document.getElementById('buyForm').submit();
    });
});

// Set the item data when the modal is shown
$('#buyModal').on('show.bs.modal', function (event) {
    var button = $(event.relatedTarget); // Button that triggered the modal
    action = button.data('action'); // Extract info from data-* attributes
    var itemsList = $('#itemsList');
    itemsList.empty(); // Clear previous data

    if (action === 'single') {
        var itemId = button.data('item-id');
        var itemName = button.data('item-name');
        var itemQuantity = button.data('item-quantity');
        console.log(itemId, itemName, itemQuantity);
        var itemHtml = `
            <div class="form-group">
                <label>${itemName}</label>
                <input type="hidden" name="item_id[]" value="${itemId}">
                <input type="hidden" name="item_name[]" value="${itemName}">
                <input type="number" class="form-control" name="quantity[]" placeholder="Enter quantity" max="${itemQuantity}" oninput="validateQuantity(this)" required>
                <div class="invalid-feedback">{% translate "Please enter a valid quantity." %}</div>
            </div>
        `;
        itemsList.append(itemHtml);
    } else if (action === 'all') {
        var tableData = assets.rows().data();
        tableData.each(function (row) {
            var itemHtml = `
                <div class="form-group">
                    <label>${row.name}</label>
                    <input type="hidden" name="item_id[]" value="${row.item_id}">
                    <input type="hidden" name="item_name[]" value="${row.name}">
                    <input type="number" class="form-control" name="quantity[]" placeholder="Enter quantity" max="${row.quantity}" oninput="validateQuantity(this)" required>
                </div>
            `;
            itemsList.append(itemHtml);
        });
        itemsList.append('<div class="text-danger d-none" id="buy-all-warning">{% translate "Please enter a valid quantity for at least one items." %}</div>');
    }
});

function setMaxQuantities() {
    $('#itemsList input[type="number"]').each(function () {
        $(this).val($(this).attr('max'));
    });
}

function validateQuantity(input) {
    var max = parseInt(input.getAttribute('max'));
    var value = parseInt(input.value);
    if (value > max) {
        input.value = max;
    }
}

function validateForm() {
    var isValid = false;
    $('#itemsList input[type="number"]').each(function () {
        var value = $(this).val();
        if (value !== '' && parseInt(value) > 0) {
            isValid = true;
            if (action === 'single') {
                $(this).removeClass('is-invalid');
                $('#buy-all-warning').addClass('d-none');
            }
        } else {
            if (action === 'single') {
                $(this).addClass('is-invalid');
            } else {
                $('#buy-all-warning').removeClass('d-none');
            }
        }
    });

    return isValid;
}
