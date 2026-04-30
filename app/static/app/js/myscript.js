// Chỉ giữ lại carousel đang dùng. Các AJAX cũ (/pluscart, /minuscart, /removecart, wishlist...) đã bỏ vì project hiện dùng /update_item/.
$(document).ready(function () {
    $('#slider1, #slider2, #slider3').owlCarousel({
        loop: true,
        margin: 20,
        responsiveClass: true,
        responsive: {
            0: { items: 2, nav: false, autoplay: true },
            600: { items: 4, nav: true, autoplay: true },
            1000: { items: 6, nav: true, loop: true, autoplay: true }
        }
    });
});
