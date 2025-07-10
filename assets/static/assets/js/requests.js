/* global assetsSettings, moment, bootstrap, loadRequestStatistics */
$(document).ready(() => {
    const urlRequests = assetsSettings.requestUrl;

    const tableRequestsVar = $('#requests');
    const RequestTable = tableRequestsVar.DataTable({
        ajax: {
            url: urlRequests,
            dataSrc: function(json) {
                return json;
            }
        },
        columns: [
            {
                data: 'id',
                render: function(data, type, row) {
                    return data;
                }
            },
            {
                data: 'order',
                render: function(data, type, row) {
                    return data;
                }
            },
            {
                data: 'requestor',
                render: function(data, type, row) {
                    return data;
                }
            },
            {
                data: 'status',
                render: function(data, type, row) {
                    return data;
                }
            },
            {
                data: 'created',
                render: function(data, type, row) {
                    if (type === 'display') {
                        return moment(data).format('L LT');
                    }
                    return data;
                }
            },
            {
                data: 'actions',
                className: 'text-end',
                render: function(data, type, row) {
                    return data;
                }
            },
        ],
        order: [[4, 'desc']],
        pageLength: 25,
        autoWidth: false,
        columnDefs: [
            { 'sortable': false, 'targets': [1, 5] },
        ],
    });
});
