/// <reference path="vendor/jquery.js" />
/// <reference path="vendor/semantic.js" />

function createSortFunc(key) {
    function f(th, td, tablesort) {
        return Number(td.data(key))
    }

    return f
}

$(function () {
    var $nominationTh = $("#nominationHead")
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

    $("#nominationSortSelect .button").on('click', function () {
        var $this = $(this)
        $this.addClass("active")
        $this.siblings().removeClass("active")
        $nominationTh.data("sortBy", createSortFunc($this.data("sort")))

        var tablesort = $('table').data('tablesort');
        if (tablesort.$th && tablesort.$th.attr('id') == "nominationHead") {
            tablesort.sort($nominationTh, tablesort.direction)
        }
    })
    $nominationTh.data("sortBy", createSortFunc("all"))
})