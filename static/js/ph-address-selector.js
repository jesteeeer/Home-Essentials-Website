const BASE_PATH = '/static/js/ph-json/';

var my_handlers = {
    fill_provinces: function () {
        var region_code = $(this).val();
        $('#region-text').val($(this).find("option:selected").text());
        $('#province-text, #city-text, #barangay-text').val('');

        $('#province').empty().append('<option selected disabled>Choose State/Province</option>');
        $('#city').empty().append('<option selected disabled></option>');
        $('#barangay').empty().append('<option selected disabled></option>');

        var url = BASE_PATH + 'province.json';
        $.getJSON(url, function (data) {
            var result = data.filter(d => d.region_code === region_code);
            result.sort((a, b) => a.province_name.localeCompare(b.province_name));
            $.each(result, (key, entry) => {
                $('#province').append(`<option value="${entry.province_code}">${entry.province_name}</option>`);
            });
        });
    },

    fill_cities: function () {
        var province_code = $(this).val();
        $('#province-text').val($(this).find("option:selected").text());
        $('#city-text, #barangay-text').val('');
        $('#city').empty().append('<option selected disabled>Choose city/municipality</option>');
        $('#barangay').empty().append('<option selected disabled></option>');

        var url = BASE_PATH + 'city.json';
        $.getJSON(url, function (data) {
            var result = data.filter(d => d.province_code === province_code);
            result.sort((a, b) => a.city_name.localeCompare(b.city_name));
            $.each(result, (key, entry) => {
                $('#city').append(`<option value="${entry.city_code}">${entry.city_name}</option>`);
            });
        });
    },

    fill_barangays: function () {
        var city_code = $(this).val();
        $('#city-text').val($(this).find("option:selected").text());
        $('#barangay-text').val('');
        $('#barangay').empty().append('<option selected disabled>Choose barangay</option>');

        var url = BASE_PATH + 'barangay.json';
        $.getJSON(url, function (data) {
            var result = data.filter(d => d.city_code === city_code);
            result.sort((a, b) => a.brgy_name.localeCompare(b.brgy_name));
            $.each(result, (key, entry) => {
                $('#barangay').append(`<option value="${entry.brgy_code}">${entry.brgy_name}</option>`);
            });
        });
    },

    onchange_barangay: function () {
        $('#barangay-text').val($(this).find("option:selected").text());
    }
};

    $(function () {
        $('#region').on('change', my_handlers.fill_provinces);
        $('#province').on('change', my_handlers.fill_cities);
        $('#city').on('change', my_handlers.fill_barangays);
        $('#barangay').on('change', my_handlers.onchange_barangay);

        let dropdown = $('#region');
        dropdown.empty().append('<option selected disabled>Choose Region</option>');
        const url = BASE_PATH + 'region.json';
        $.getJSON(url, function (data) {
            console.log("Loaded Regions:", data);
            $.each(data, (key, entry) => {
                dropdown.append(`<option value="${entry.region_code}">${entry.region_name}</option>`);
            });
        });

});
