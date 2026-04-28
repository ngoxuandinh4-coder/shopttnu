// --- 2. LOGIC TÍCH CHỌN & THANH TOÁN (TRONG TRANG CART) ---
    const selectAll = document.getElementById('select-all');
    const itemCheckboxes = document.querySelectorAll('.item-checkbox');
    const selectedCount = document.getElementById('selected-count');
    const selectedTotal = document.getElementById('selected-total');
    const checkoutBtn = document.getElementById('checkout-selected-btn'); 
    const sizeDisplay = document.getElementById('selected-sizes-display'); // ID vùng hiển thị size

    // Hàm 1: Tính toán tiền và hiện Size
    function updateSummary() {
        let count = 0;
        let total = 0;
        let selectedSizes = []; // Mảng chứa size

        document.querySelectorAll('.item-checkbox:checked').forEach(checkbox => {
            count++;
            total += parseFloat(checkbox.dataset.total || 0);

            // Lấy và kiểm tra size
            let sizeValue = checkbox.dataset.size;
            if (sizeValue && sizeValue.trim() !== "" && sizeValue !== "None") {
                selectedSizes.push(sizeValue.trim());
            } else {
                selectedSizes.push("Mặc định");
            }
        });

        // In ra màn hình số lượng và tổng tiền
        if (selectedCount) selectedCount.innerText = count;
        if (selectedTotal) selectedTotal.innerText = total.toLocaleString('vi-VN');

        // In ra màn hình các Size đã chọn (lọc trùng lặp)
        if (sizeDisplay) {
            if (selectedSizes.length > 0) {
                let uniqueSizes = [...new Set(selectedSizes)];
                sizeDisplay.innerText = uniqueSizes.join(', ');
            } else {
                sizeDisplay.innerText = "Chưa có";
            }
        }
    }

    // Hàm 2: Ẩn/Hiện nút Thanh toán
    function toggleCheckoutButton() {
        const checkedCount = document.querySelectorAll('.item-checkbox:checked').length;
        
        if (checkoutBtn) {
            if (checkedCount > 0) {
                // Sáng nút, cho phép bấm
                checkoutBtn.disabled = false;
                checkoutBtn.style.opacity = "1";
                checkoutBtn.style.cursor = "pointer";
                checkoutBtn.innerHTML = '<i class="fas fa-check-circle me-2"></i>THANH TOÁN NGAY';
            } else {
                // Mờ nút, vô hiệu hóa
                checkoutBtn.disabled = true;
                checkoutBtn.style.opacity = "0.5";
                checkoutBtn.style.cursor = "not-allowed";
                checkoutBtn.innerHTML = 'VUI LÒNG CHỌN SẢN PHẨM';
            }
        }
    }

    // Sự kiện khi bấm "Chọn tất cả"
    if (selectAll) {
        selectAll.addEventListener('change', function () {
            itemCheckboxes.forEach(checkbox => {
                checkbox.checked = selectAll.checked;
            });
            updateSummary();
            toggleCheckoutButton(); // Gọi hàm cập nhật nút
        });
    }

    // Sự kiện khi tích từng ô checkbox
    itemCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSummary();
            toggleCheckoutButton(); // Gọi hàm cập nhật nút
            
            // Bỏ tích 1 ô thì tắt luôn nút "Chọn tất cả"
            if (!this.checked && selectAll) selectAll.checked = false;
        });
    });

    // Sự kiện khi bấm nút Thanh Toán (Chuyển hướng)
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function () {
            let params = new URLSearchParams();
            let hasSelected = false;

            document.querySelectorAll('.item-checkbox:checked').forEach(checkbox => {
                params.append('id', checkbox.dataset.product);
                params.append('size', checkbox.dataset.size || "");
                hasSelected = true;
            });

            if (!hasSelected) {
                alert("Vui lòng tích chọn ít nhất một sản phẩm để thanh toán!");
                return;
            }
            window.location.href = '/checkout/?' + params.toString();
        });
    }

    // Chạy các hàm này 1 lần ngay khi load trang để reset mọi thứ về 0
    updateSummary();
    toggleCheckoutButton();
; // Kết thúc khối DOMContentLoaded