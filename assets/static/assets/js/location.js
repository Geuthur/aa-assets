/* global assetsSettings */

$(document).ready(function() {
    const locationTableVar = $('#location');

    const tableLocation = locationTableVar.DataTable({
        ajax: {
            url: assetsSettings.locationUrl,
            type: 'GET',
            dataSrc: function (json) {
                return json;
            },
            error: function (xhr, error, thrown) {
                console.error('Error loading data:', error);
                tableLocation.clear().draw();
            }
        },
        columns: [
            {
                data: 'location_id',
                render: function (data, type) {
                    return data;
                }
            },
            {
                data: 'name',
                render: function (data, type, row) {
                    return data;
                }
            },
            {
                data: 'solar_system',
                render: function (data, type) {
                    return data;
                }
            },
            {
                data: 'view',
                render: function (data, type, row) {
                    return data;
                }
            }
        ],
        columnDefs: [
            {
                targets: 3,
                className: 'text-end',
                orderable: false,
                searchable: false
            }
        ],
        order: [
            [0, 'asc']
        ],
        pageLength: 25,
    });

    tableLocation.on('draw', function() {
        $('[data-tooltip-toggle="assets-tooltip"]').tooltip({
            trigger: 'hover',
        });
    });
});
