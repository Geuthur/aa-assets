/* global assetsSettings, translations */

$(document).ready(() => {
    const AssetsTableVar = $('#assets');

    let LocationID = null;
    let LocationFLAG = null;

    const tableAssets = AssetsTableVar.DataTable({
        ajax: {
            url: assetsSettings.assetsUrl,
            type: 'GET',
            dataSrc: function(data) {
                LocationID = data.location_id;
                LocationFLAG = data.location_flag;
                return data.assets;
            }
        },
        columns: [
            {
                data: 'item_id',
                render: function(data, _, __) {
                    return '<img class="card-img-zoom" src="https://imageserver.eveonline.com/types/' + data + '/icon/?size=64" height="64" width="64"/>';
                }
            },
            {
                data: 'name',
                render: function(data, _, __) {
                    return data;
                }
            },
            {
                data: 'quantity',
                render: function (data, _, __) {
                    return data;
                }
            },
            {
                data: 'location',
                render: function (data, _, __) {
                    return data;
                }
            },
            {
                data: 'price',
                render: function (data, type, row) {
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
                data: null,
                render: function(data, type, row) {
                    return `
                        <button type="button"
                            class="btn btn-primary"
                            data-bs-toggle="modal"
                            data-bs-target="#assets-single-request"
                            data-action="${assetsSettings.createRequestUrl}"
                            aria-label="Request Order"
                            data-asset-pk="${row.asset_pk}"
                            data-item-id="${row.item_id}"
                            data-item-quantity="${row.quantity}"
                            data-title="${row.name}"
                        >
                            ${translations.buy}
                        </button>
                    `;
                }
            }
        ],
        order: [[1, 'asc']],
        pageLength: 25,
        autoWidth: false,
        columnDefs: [
            { 'sortable': false, 'targets': [0, 5] },
        ],
        footerCallback: function (_, data, __, ___, ____) {
            const api = this.api();
            const footer = $(api.table().footer());

            // Überprüfen, ob Daten vorhanden sind
            if (data.length > 0) {
                footer.html(`
                    <button type="button"
                        class="btn btn-primary text-nowrap mt-4" data-bs-toggle="modal"
                        data-bs-target="#assets-multi-request"
                        data-title="${translations.multiBuy}"
                        data-location-id="${LocationID}"
                        data-location-flag="${LocationFLAG}"
                        data-action="${assetsSettings.createRequestUrl}"
                        aria-label="Request Order"
                    >
                        ${translations.multiBuy}
                    </button>
                `);
            } else {
                footer.empty(); // Leeren des Footers, wenn keine Daten vorhanden sind
            }
        }
    });

});
