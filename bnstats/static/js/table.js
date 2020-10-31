/// <reference path="vendor/jquery.js" />
/// <reference path="vendor/semantic.js" />

$(function () {
    $('table').tablesort()

    $('thead th.number').data('sortBy', function (th, td, tablesort) {
        var num = td.data("sort-value") | td.text()
        return new Number(num);
    });

    $('thead th.float').data('sortBy', function (th, td, tablesort) {
        var num = td.data("sort-value") | td.text()
        return parseFloat(num);
    });

    $('tr').on('click', function () {
        var $this = $(this)
        var target = $this.data("url")

        if (target)
            window.open(target)
    })
})