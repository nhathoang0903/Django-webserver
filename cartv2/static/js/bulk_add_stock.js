/**
 * Bulk Add Stock Functionality
 * This file contains the JavaScript needed for the bulk add stock modal
 */
function initBulkAddStock() {
    // Get DOM elements
    const bulkSearchProduct = document.getElementById('bulkSearchProduct');
    const bulkCategoryFilter = document.getElementById('bulkCategoryFilter');
    const bulkSortBy = document.getElementById('bulkSortBy');
    const bulkSelectAllBtn = document.getElementById('bulkSelectAllBtn');
    const bulkClearSelectionsBtn = document.getElementById('bulkClearSelectionsBtn');
    const bulkAddStockBtn = document.getElementById('bulkAddStockBtn');
    const bulkProductsContainer = document.getElementById('bulkProductsContainer');
    const selectedProductsTable = document.getElementById('selectedProductsTable');
    const selectedProductsTableBody = selectedProductsTable.querySelector('tbody');
    const noProductsSelectedMsg = document.getElementById('noProductsSelectedMsg');

    // Object to track selected products
    let selectedProducts = {};
    let selectedCountBadge = document.getElementById('selectedCountBadge');
    const totalProductsCount = document.getElementById('totalProductsCount');

    // Initialize when the modal is shown
    $('#bulkAddStockModal').on('shown.bs.modal', function() {
        // Reset selections
        selectedProducts = {};

        // Format product names in bulk modal
        formatProductNames();

        // Count total products and update badge
        const totalProducts = bulkProductsContainer.querySelectorAll('.bulk-product-item').length;
        totalProductsCount.textContent = `${totalProducts} products in database`;

        // Initial sort and filter
        sortAndFilterBulkProducts();
        updateSelectedProductsTable();
        updateSelectionCount();
    });

    // Format product names in the bulk modal
    function formatProductNames() {
        document.querySelectorAll('.bulk-product-item').forEach(item => {
            const productNameElement = item.querySelector('.product-label');
            if (productNameElement) {
                const rawName = item.dataset.productName;
                const displayName = rawName.replace(/_/g, ' ');

                // Update the text content preserving the stock info
                const stockInfoMatch = productNameElement.textContent.match(/\(\d+ in stock\)/);
                const stockInfo = stockInfoMatch ? stockInfoMatch[0] : '';
                productNameElement.textContent = displayName + ' ' + stockInfo;

                // Store display name in dataset for easier access
                item.dataset.displayName = displayName;
            }
        });
    }

    // Event listeners for search and filter
    bulkSearchProduct.addEventListener('input', sortAndFilterBulkProducts);
    bulkCategoryFilter.addEventListener('change', sortAndFilterBulkProducts);
    bulkSortBy.addEventListener('change', sortAndFilterBulkProducts);

    // Select all visible products
    bulkSelectAllBtn.addEventListener('click', function() {
        const visibleProducts = Array.from(document.querySelectorAll('#bulkProductsContainer .bulk-product-item:not([style*="display: none"])'));

        visibleProducts.forEach(product => {
            const productId = product.getAttribute('data-product-id');
            const productName = product.getAttribute('data-product-name');
            const displayName = product.getAttribute('data-display-name') || productName.replace(/_/g, ' ');

            // Get current stock from the product-label text
            const productLabel = product.querySelector('.product-label');
            const stockMatch = productLabel.textContent.match(/\((\d+) in stock\)/);
            const initialStock = stockMatch ? stockMatch[1] : '0';

            // Get quantity from input
            const quantityInput = product.querySelector('.bulk-quantity-input');
            const quantity = quantityInput ? quantityInput.value : 1;

            if (!selectedProducts[productId]) {
                selectedProducts[productId] = {
                    id: productId,
                    name: productName,
                    displayName: displayName,
                    initialStock: initialStock,
                    quantity: quantity
                };
            }

            // Update button appearance to selected state
            const addButton = product.querySelector('.add-product-btn');
            if (addButton) {
                addButton.classList.remove('btn-outline-primary');
                addButton.classList.add('btn-success');
                addButton.innerHTML = '<i class="fas fa-check"></i>';
            }
        });

        updateSelectedProductsTable();
        updateSelectionCount();
    });

    // Clear all selections
    bulkClearSelectionsBtn.addEventListener('click', function() {
        // Reset all add buttons to default state
        const allAddButtons = bulkProductsContainer.querySelectorAll('.add-product-btn');
        allAddButtons.forEach(button => {
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-primary');
            button.innerHTML = '<i class="fas fa-plus"></i>';
        });

        selectedProducts = {};
        updateSelectedProductsTable();
        updateSelectionCount();
    });

    // Add event listener for product selection buttons
    bulkProductsContainer.addEventListener('click', function(e) {
        const addButton = e.target.closest('.add-product-btn');
        if (!addButton) return;

        const productItem = addButton.closest('.bulk-product-item');
        const productId = productItem.getAttribute('data-product-id');
        const productName = productItem.getAttribute('data-product-name');
        const displayName = productItem.getAttribute('data-display-name') || productName.replace(/_/g, ' ');

        // Get current stock from the product-label text
        const productLabel = productItem.querySelector('.product-label');
        const stockMatch = productLabel.textContent.match(/\((\d+) in stock\)/);
        const initialStock = stockMatch ? stockMatch[1] : '0';

        // Get quantity from input
        const quantityInput = productItem.querySelector('.bulk-quantity-input');
        const quantity = quantityInput ? quantityInput.value : 1;

        if (selectedProducts[productId]) {
            // Product is already selected, so deselect it
            delete selectedProducts[productId];
            addButton.classList.remove('btn-success');
            addButton.classList.add('btn-outline-primary');
            addButton.innerHTML = '<i class="fas fa-plus"></i>';
        } else {
            // Product is not selected, so select it
            selectedProducts[productId] = {
                id: productId,
                name: productName,
                displayName: displayName,
                initialStock: initialStock,
                quantity: quantity
            };
            addButton.classList.remove('btn-outline-primary');
            addButton.classList.add('btn-success');
            addButton.innerHTML = '<i class="fas fa-check"></i>';
        }

        updateSelectedProductsTable();
        updateSelectionCount();
    });

    // Update quantity when input changes in product list
    bulkProductsContainer.addEventListener('input', function(e) {
        if (e.target.classList.contains('bulk-quantity-input')) {
            const productItem = e.target.closest('.bulk-product-item');
            const productId = productItem.getAttribute('data-product-id');

            if (selectedProducts[productId]) {
                selectedProducts[productId].quantity = e.target.value;
                updateSelectedProductsTable();
            }
        }
    });

    // Update quantity when changed in the selected products table
    selectedProductsTable.addEventListener('input', function(e) {
        if (e.target.classList.contains('quantity-input')) {
            const productId = e.target.dataset.productId;
            if (selectedProducts[productId]) {
                selectedProducts[productId].quantity = e.target.value;

                // Also update the corresponding quantity in the products list
                const productItem = bulkProductsContainer.querySelector(`.bulk-product-item[data-product-id="${productId}"]`);
                if (productItem) {
                    const quantityInput = productItem.querySelector('.bulk-quantity-input');
                    if (quantityInput) {
                        quantityInput.value = e.target.value;
                    }
                }
            }
        }
    });

    // Remove product from selection
    selectedProductsTable.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-product-btn') || e.target.closest('.remove-product-btn')) {
            const button = e.target.classList.contains('remove-product-btn') ? e.target : e.target.closest('.remove-product-btn');
            const productId = button.dataset.productId;

            // Update button state in the product list
            const productItem = bulkProductsContainer.querySelector(`.bulk-product-item[data-product-id="${productId}"]`);
            if (productItem) {
                const addButton = productItem.querySelector('.add-product-btn');
                if (addButton) {
                    addButton.classList.remove('btn-success');
                    addButton.classList.add('btn-outline-primary');
                    addButton.innerHTML = '<i class="fas fa-plus"></i>';
                }
            }

            delete selectedProducts[productId];
            updateSelectedProductsTable();
            updateSelectionCount();
        }
    });

    // Add stock to all selected products
    bulkAddStockBtn.addEventListener('click', function() {
        const selectedProductsArr = Object.values(selectedProducts);
        if (selectedProductsArr.length === 0) {
            alert('Please select at least one product');
            return;
        }

        // Validate quantities
        let hasInvalidQuantity = false;
        selectedProductsArr.forEach(product => {
            const quantity = parseInt(product.quantity);
            if (isNaN(quantity) || quantity <= 0) {
                hasInvalidQuantity = true;
            }
        });

        if (hasInvalidQuantity) {
            alert('Please enter valid quantities (greater than 0) for all selected products');
            return;
        }

        // Show loading state
        const originalText = bulkAddStockBtn.innerHTML;
        bulkAddStockBtn.disabled = true;
        bulkAddStockBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Adding Stock...';

        const notes = document.getElementById('bulkStockNotes').value;

        // Process each product sequentially to avoid race conditions
        addStockSequentially(selectedProductsArr, notes, 0)
            .then(results => {
                console.log('Stock added successfully:', results);

                // Show success toast
                const toast = new bootstrap.Toast(document.getElementById('stockSuccessToast'));
                toast.show();

                // Close modal and reset
                const modal = bootstrap.Modal.getInstance(document.getElementById('bulkAddStockModal'));
                if (modal) {
                    modal.hide();
                } else {
                    // Fallback if bootstrap instance not available
                    $('#bulkAddStockModal').modal('hide');
                }

                bulkClearSelectionsBtn.click();
                document.getElementById('bulkStockNotes').value = '';

                // Reload page after delay
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            })
            .catch(error => {
                console.error('Error adding stock:', error);
                alert('An error occurred while adding stock: ' + error.message);
            })
            .finally(() => {
                // Reset button state
                bulkAddStockBtn.disabled = false;
                bulkAddStockBtn.innerHTML = originalText;
            });
    });

    // Helper function to sort and filter products in the bulk modal
    function sortAndFilterBulkProducts() {
        const searchTerm = bulkSearchProduct.value.toLowerCase();
        const selectedCategory = bulkCategoryFilter.value.toLowerCase();
        const sortOption = bulkSortBy.value;

        // Step 1: Filter products
        const productItems = bulkProductsContainer.querySelectorAll('.bulk-product-item');
        const visibleProducts = [];

        productItems.forEach(item => {
            // Use displayName (with spaces) for search if available
            const productName = (item.dataset.displayName || item.dataset.productName).toLowerCase();
            const category = item.dataset.category.toLowerCase();

            const matchesSearch = productName.includes(searchTerm);
            const matchesCategory = !selectedCategory || category === selectedCategory;

            const isVisible = matchesSearch && matchesCategory;
            item.style.display = isVisible ? 'block' : 'none';

            if (isVisible) {
                visibleProducts.push(item);
            }
        });

        // Step 2: Sort visible products
        const sortedProducts = [...visibleProducts].sort((a, b) => {
            const nameA = (a.dataset.displayName || a.dataset.productName).toLowerCase();
            const nameB = (b.dataset.displayName || b.dataset.productName).toLowerCase();
            const stockA = parseInt(a.dataset.stock || 0);
            const stockB = parseInt(b.dataset.stock || 0);

            switch (sortOption) {
                case 'name_desc':
                    return nameB.localeCompare(nameA);
                case 'stock_asc':
                    return stockA - stockB;
                case 'stock_desc':
                    return stockB - stockA;
                case 'name':
                default:
                    return nameA.localeCompare(nameB);
            }
        });

        // Step 3: Reorder the products in the DOM
        const container = bulkProductsContainer;
        sortedProducts.forEach(product => {
            container.appendChild(product);
        });

        // Update total visible products count
        const totalProductsCount = document.getElementById('totalProductsCount');
        const totalProducts = bulkProductsContainer.querySelectorAll('.bulk-product-item').length;
        const visibleProductsCount = visibleProducts.length;

        totalProductsCount.textContent =
            (searchTerm || selectedCategory) ?
            `${visibleProductsCount} / ${totalProducts} products` :
            `${totalProducts} products in database`;
    }

    // Helper function to update the selected products table
    function updateSelectedProductsTable() {
        selectedProductsTableBody.innerHTML = '';

        const selectedProductsArr = Object.values(selectedProducts);

        if (selectedProductsArr.length === 0) {
            selectedProductsTable.style.display = 'none';
            noProductsSelectedMsg.style.display = 'block';
            return;
        }

        selectedProductsTable.style.display = 'table';
        noProductsSelectedMsg.style.display = 'none';

        // Sort products by name for consistent display
        selectedProductsArr.sort((a, b) => (a.displayName || a.name).localeCompare(b.displayName || b.name));

        selectedProductsArr.forEach(product => {
            // Use displayName if available, otherwise fallback to formatted name
            const displayName = product.displayName || product.name.replace(/_/g, ' ');

            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${displayName}</td>
                <td class="text-center">${product.initialStock}</td>
                <td class="text-center">
                    <input type="number" class="form-control form-control-sm quantity-input" 
                           data-product-id="${product.id}" min="1" value="${product.quantity}" style="width: 70px; margin: 0 auto;">
                </td>
                <td class="text-center">
                    <button class="btn btn-sm btn-outline-danger remove-product-btn" data-product-id="${product.id}">
                        <i class="fas fa-times"></i>
                    </button>
                </td>
            `;
            selectedProductsTableBody.appendChild(row);
        });
    }

    // Helper function to add stock to products sequentially
    async function addStockSequentially(products, notes, index) {
        if (index >= products.length) {
            return []; // Done with all products
        }

        const product = products[index];
        const result = await addStockToProduct(product.id, product.quantity, notes);

        // Continue with next product
        const remainingResults = await addStockSequentially(products, notes, index + 1);
        return [result, ...remainingResults];
    }

    // Helper function to add stock to a single product
    async function addStockToProduct(productId, quantity, notes) {
        try {
            const response = await fetch('/api/product/add-stock/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({
                    product_id: parseInt(productId),
                    quantity: parseInt(quantity),
                    notes: notes
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to add stock');
            }

            return response.json();
        } catch (error) {
            console.error(`Error adding stock to product ${productId}:`, error);
            throw error;
        }
    }

    // Helper function to update the selection count
    function updateSelectionCount() {
        const count = Object.keys(selectedProducts).length;
        selectedCountBadge.textContent = count;
    }
}

// Initialize the bulk add stock functionality when the document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if the bulk add stock modal exists on the page
    if (document.getElementById('bulkAddStockModal')) {
        initBulkAddStock();
    }
});