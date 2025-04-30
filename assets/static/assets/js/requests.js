/* global assetsSettings, moment, bootstrap, loadRequestStatistics */
$(document).ready(() => {
    const urlRequests = assetsSettings.requestUrl;
    const urlMyRequests = assetsSettings.myRequestUrl;

    const tableRequestsVar = $('#requests');
    const tableMyRequestsVar = $('#my-requests');

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

    const MyRequestTable = tableMyRequestsVar.DataTable({
        ajax: {
            url: urlMyRequests,
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

    window.loadRequestStatistics = function () {
        $.ajax({
            url: assetsSettings.statisticsUrl, // URL für die Statistikdaten
            type: 'GET',
            dataType: 'json',
            success: function (data) {
                const requestCountElement = document.getElementById('request-count');
                const myRequestCountElement = document.getElementById('my-request-count');

                if (requestCountElement) {
                    const requestCount = data.requestCount || 0;
                    requestCountElement.textContent = requestCount;
                    requestCountElement.classList.toggle('d-none', requestCount === 0);
                }

                if (myRequestCountElement) {
                    const myRequestCount = data.myRequestCount || 0;
                    myRequestCountElement.textContent = myRequestCount;
                    myRequestCountElement.classList.toggle('d-none', myRequestCount === 0);
                }
            },
            error: function (xhr, status, error) {
                console.error('Fehler beim Abrufen der Statistikdaten:', error);
            }
        });
    };
    loadRequestStatistics(); // Initialer Aufruf der Funktion
});
