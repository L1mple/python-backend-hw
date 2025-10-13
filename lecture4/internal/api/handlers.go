package api

import (
	"context"
	"database/sql"
	"net/http"
	"strconv"

	"lecture4/internal/repository"

	"github.com/gin-gonic/gin"
	"github.com/lib/pq"
)

type Handler struct {
	queries *repository.Queries
	db      *sql.DB
}

func NewHandler(db *sql.DB) *Handler {
	return &Handler{
		queries: repository.New(db),
		db:      db,
	}
}

// itemToResponse преобразует модель Item в ItemResponse
func itemToResponse(item repository.Item) ItemResponse {
	return ItemResponse{
		ID:      item.ID,
		Name:    item.Name,
		Price:   item.Price,
		Deleted: item.Deleted,
	}
}

// cartItemsToResponse преобразует список GetCartItemsRow в CartItemResponse
func cartItemsToResponse(items []repository.GetCartItemsRow) []CartItemResponse {
	result := make([]CartItemResponse, 0, len(items))
	for _, ci := range items {
		result = append(result, CartItemResponse{
			ID:        ci.ItemID,
			Name:      ci.Name,
			Quantity:  ci.Quantity,
			Available: !ci.Deleted,
		})
	}
	return result
}

// cartItemsForCartsToResponse преобразует список GetCartItemsForCartsRow в CartItemResponse
func cartItemsForCartsToResponse(items []repository.GetCartItemsForCartsRow) []CartItemResponse {
	result := make([]CartItemResponse, 0, len(items))
	for _, ci := range items {
		result = append(result, CartItemResponse{
			ID:        ci.ItemID,
			Name:      ci.Name,
			Quantity:  ci.Quantity,
			Available: !ci.Deleted,
		})
	}
	return result
}

// buildCartResponse строит полный ответ с информацией о корзине
func (h *Handler) buildCartResponse(ctx context.Context, cartID int32) (CartResponse, error) {
	cartItems, err := h.queries.GetCartItems(ctx, cartID)
	if err != nil {
		return CartResponse{}, err
	}

	totalPrice, err := h.queries.GetCartTotalPrice(ctx, cartID)
	if err != nil {
		return CartResponse{}, err
	}

	items := cartItemsToResponse(cartItems)

	return CartResponse{
		ID:    cartID,
		Items: items,
		Price: totalPrice,
	}, nil
}

// PostItem godoc
// @Summary Создать товар
// @Description Создает новый товар
// @Tags items
// @Accept json
// @Produce json
// @Param item body ItemRequest true "Данные товара"
// @Success 201 {object} ItemResponse
// @Failure 400 {object} ErrorResponse
// @Router /item [post]
func (h *Handler) PostItem(c *gin.Context) {
	var req ItemRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: err.Error()})
		return
	}

	item, err := h.queries.CreateItem(c.Request.Context(), repository.CreateItemParams{
		Name:  req.Name,
		Price: req.Price,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	c.Header("Location", "/item/"+strconv.Itoa(int(item.ID)))
	c.JSON(http.StatusCreated, itemToResponse(item))
}

// GetItemByID godoc
// @Summary Получить товар по ID
// @Description Получает товар по его ID
// @Tags items
// @Produce json
// @Param id path int true "ID товара"
// @Success 200 {object} ItemResponse
// @Failure 404 {object} ErrorResponse
// @Router /item/{id} [get]
func (h *Handler) GetItemByID(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: "Invalid item ID"})
		return
	}

	item, err := h.queries.GetItem(c.Request.Context(), int32(id))
	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, ErrorResponse{Message: "Item with id=" + c.Param("id") + " not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	if item.Deleted {
		c.JSON(http.StatusNotFound, ErrorResponse{Message: "Item with id=" + c.Param("id") + " not found"})
		return
	}

	c.JSON(http.StatusOK, itemToResponse(item))
}

// GetItems godoc
// @Summary Получить список товаров
// @Description Получает список товаров с фильтрацией и пагинацией
// @Tags items
// @Produce json
// @Param offset query int false "Смещение" default(0)
// @Param limit query int false "Лимит" default(10)
// @Param min_price query number false "Минимальная цена"
// @Param max_price query number false "Максимальная цена"
// @Param show_deleted query bool false "Показывать удаленные" default(false)
// @Success 200 {array} ItemResponse
// @Router /item [get]
func (h *Handler) GetItems(c *gin.Context) {
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))
	showDeleted := c.DefaultQuery("show_deleted", "false") == "true"

	var minPrice, maxPrice sql.NullString
	if minPriceStr := c.Query("min_price"); minPriceStr != "" {
		if _, err := strconv.ParseFloat(minPriceStr, 64); err == nil {
			minPrice = sql.NullString{String: minPriceStr, Valid: true}
		}
	}
	if maxPriceStr := c.Query("max_price"); maxPriceStr != "" {
		if _, err := strconv.ParseFloat(maxPriceStr, 64); err == nil {
			maxPrice = sql.NullString{String: maxPriceStr, Valid: true}
		}
	}

	items, err := h.queries.GetItems(c.Request.Context(), repository.GetItemsParams{
		Limit:       int32(limit),
		Offset:      int32(offset),
		ShowDeleted: showDeleted,
		MinPrice:    minPrice,
		MaxPrice:    maxPrice,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	result := make([]ItemResponse, 0, len(items))
	for _, item := range items {
		result = append(result, itemToResponse(item))
	}

	c.JSON(http.StatusOK, result)
}

// PutItem godoc
// @Summary Обновить товар
// @Description Полностью обновляет существующий товар
// @Tags items
// @Accept json
// @Produce json
// @Param id path int true "ID товара"
// @Param item body ItemRequest true "Данные товара"
// @Success 200 {object} ItemResponse
// @Failure 304 {object} ErrorResponse
// @Failure 400 {object} ErrorResponse
// @Router /item/{id} [put]
func (h *Handler) PutItem(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: "Invalid item ID"})
		return
	}

	var req ItemRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: err.Error()})
		return
	}

	// Проверяем, существует ли товар
	existingItem, err := h.queries.GetItem(c.Request.Context(), int32(id))
	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotModified, ErrorResponse{Message: "Item with id=" + c.Param("id") + " not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	if existingItem.Deleted {
		c.JSON(http.StatusNotModified, ErrorResponse{Message: "Item with id=" + c.Param("id") + " not found"})
		return
	}

	item, err := h.queries.UpdateItem(c.Request.Context(), repository.UpdateItemParams{
		ID:    int32(id),
		Name:  req.Name,
		Price: req.Price,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, itemToResponse(item))
}

// PatchItem godoc
// @Summary Частично обновить товар
// @Description Частично обновляет существующий товар (кроме поля deleted)
// @Tags items
// @Accept json
// @Produce json
// @Param id path int true "ID товара"
// @Param item body PatchItemRequest true "Данные для обновления"
// @Success 200 {object} ItemResponse
// @Failure 304 {object} ErrorResponse
// @Failure 400 {object} ErrorResponse
// @Router /item/{id} [patch]
func (h *Handler) PatchItem(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: "Invalid item ID"})
		return
	}

	var req PatchItemRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: err.Error()})
		return
	}

	var item repository.Item
	if req.Name != nil && req.Price != nil {
		item, err = h.queries.PatchItemBoth(c.Request.Context(), repository.PatchItemBothParams{
			ID:    int32(id),
			Name:  *req.Name,
			Price: *req.Price,
		})
	} else if req.Name != nil {
		item, err = h.queries.PatchItemName(c.Request.Context(), repository.PatchItemNameParams{
			ID:   int32(id),
			Name: *req.Name,
		})
	} else if req.Price != nil {
		item, err = h.queries.PatchItemPrice(c.Request.Context(), repository.PatchItemPriceParams{
			ID:    int32(id),
			Price: *req.Price,
		})
	} else {
		// Нет полей для обновления - возвращаем текущий товар
		existingItem, err := h.queries.GetItem(c.Request.Context(), int32(id))
		if err != nil {
			if err == sql.ErrNoRows {
				c.JSON(http.StatusNotModified, ErrorResponse{Message: "Item with id=" + c.Param("id") + " not found or is deleted"})
				return
			}
			c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
			return
		}
		if existingItem.Deleted {
			c.JSON(http.StatusNotModified, ErrorResponse{Message: "Item with id=" + c.Param("id") + " not found or is deleted"})
			return
		}
		c.JSON(http.StatusOK, itemToResponse(existingItem))
		return
	}

	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotModified, ErrorResponse{Message: "Item with id=" + c.Param("id") + " not found or is deleted"})
			return
		}
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, itemToResponse(item))
}

// DeleteItem godoc
// @Summary Удалить товар
// @Description Помечает товар как удаленный
// @Tags items
// @Param id path int true "ID товара"
// @Success 200
// @Router /item/{id} [delete]
func (h *Handler) DeleteItem(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: "Invalid item ID"})
		return
	}

	err = h.queries.DeleteItem(c.Request.Context(), int32(id))
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	c.Status(http.StatusOK)
}

// PostCart godoc
// @Summary Создать корзину
// @Description Создает новую пустую корзину
// @Tags carts
// @Produce json
// @Success 201 {object} CartIdResponse
// @Router /cart [post]
func (h *Handler) PostCart(c *gin.Context) {
	cart, err := h.queries.CreateCart(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	c.Header("Location", "/cart/"+strconv.Itoa(int(cart.ID)))
	c.JSON(http.StatusCreated, CartIdResponse{ID: cart.ID})
}

// GetCartByID godoc
// @Summary Получить корзину по ID
// @Description Получает корзину по её ID с расчетом общей стоимости
// @Tags carts
// @Produce json
// @Param id path int true "ID корзины"
// @Success 200 {object} CartResponse
// @Failure 404 {object} ErrorResponse
// @Router /cart/{id} [get]
func (h *Handler) GetCartByID(c *gin.Context) {
	id, err := strconv.Atoi(c.Param("id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: "Invalid cart ID"})
		return
	}

	cart, err := h.queries.GetCart(c.Request.Context(), int32(id))
	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, ErrorResponse{Message: "Cart with id=" + c.Param("id") + " not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	cartResponse, err := h.buildCartResponse(c.Request.Context(), cart.ID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, cartResponse)
}

// GetCarts godoc
// @Summary Получить список корзин
// @Description Получает список корзин с фильтрацией и пагинацией
// @Tags carts
// @Produce json
// @Param offset query int false "Смещение" default(0)
// @Param limit query int false "Лимит" default(10)
// @Param min_price query number false "Минимальная цена"
// @Param max_price query number false "Максимальная цена"
// @Param min_quantity query int false "Минимальное количество товаров"
// @Param max_quantity query int false "Максимальное количество товаров"
// @Success 200 {array} CartResponse
// @Router /cart [get]
func (h *Handler) GetCarts(c *gin.Context) {
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "10"))

	var minPrice, maxPrice sql.NullString
	var minQuantity, maxQuantity sql.NullInt32

	if minPriceStr := c.Query("min_price"); minPriceStr != "" {
		if _, err := strconv.ParseFloat(minPriceStr, 64); err == nil {
			minPrice = sql.NullString{String: minPriceStr, Valid: true}
		}
	}
	if maxPriceStr := c.Query("max_price"); maxPriceStr != "" {
		if _, err := strconv.ParseFloat(maxPriceStr, 64); err == nil {
			maxPrice = sql.NullString{String: maxPriceStr, Valid: true}
		}
	}
	if minQtyStr := c.Query("min_quantity"); minQtyStr != "" {
		if val, err := strconv.Atoi(minQtyStr); err == nil {
			minQuantity = sql.NullInt32{Int32: int32(val), Valid: true}
		}
	}
	if maxQtyStr := c.Query("max_quantity"); maxQtyStr != "" {
		if val, err := strconv.Atoi(maxQtyStr); err == nil {
			maxQuantity = sql.NullInt32{Int32: int32(val), Valid: true}
		}
	}

	carts, err := h.queries.GetAllCartsWithStats(c.Request.Context(), repository.GetAllCartsWithStatsParams{
		Limit:       int32(limit),
		Offset:      int32(offset),
		MinPrice:    minPrice,
		MaxPrice:    maxPrice,
		MinQuantity: minQuantity,
		MaxQuantity: maxQuantity,
	})
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	cartIDs := make([]int32, len(carts))
	for i, cart := range carts {
		cartIDs[i] = cart.ID
	}

	var allCartItems []repository.GetCartItemsForCartsRow
	if len(cartIDs) > 0 {
		allCartItems, err = h.queries.GetCartItemsForCarts(c.Request.Context(), cartIDs)
		if err != nil {
			c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
			return
		}
	}

	// Группируем товары по корзинам
	cartItemsMap := make(map[int32][]repository.GetCartItemsForCartsRow)
	for _, ci := range allCartItems {
		cartItemsMap[ci.CartID] = append(cartItemsMap[ci.CartID], ci)
	}

	result := make([]CartResponse, 0, len(carts))
	for _, cart := range carts {
		items := cartItemsForCartsToResponse(cartItemsMap[cart.ID])

		result = append(result, CartResponse{
			ID:    cart.ID,
			Items: items,
			Price: cart.TotalPrice,
		})
	}

	c.JSON(http.StatusOK, result)
}

// AddItemToCart godoc
// @Summary Добавить товар в корзину
// @Description Добавляет товар в корзину или увеличивает его количество
// @Tags carts
// @Produce json
// @Param cart_id path int true "ID корзины"
// @Param item_id path int true "ID товара"
// @Success 200 {object} CartResponse
// @Failure 404 {object} ErrorResponse
// @Router /cart/{cart_id}/add/{item_id} [post]
func (h *Handler) AddItemToCart(c *gin.Context) {
	cartID, err := strconv.Atoi(c.Param("cart_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: "Invalid cart ID"})
		return
	}

	itemID, err := strconv.Atoi(c.Param("item_id"))
	if err != nil {
		c.JSON(http.StatusBadRequest, ErrorResponse{Message: "Invalid item ID"})
		return
	}

	// Проверяем существование корзины
	_, err = h.queries.GetCart(c.Request.Context(), int32(cartID))
	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, ErrorResponse{Message: "Cart with id=" + c.Param("cart_id") + " or item with id=" + c.Param("item_id") + " not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	// Проверяем существование товара
	_, err = h.queries.GetItem(c.Request.Context(), int32(itemID))
	if err != nil {
		if err == sql.ErrNoRows {
			c.JSON(http.StatusNotFound, ErrorResponse{Message: "Cart with id=" + c.Param("cart_id") + " or item with id=" + c.Param("item_id") + " not found"})
			return
		}
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	// Добавляем товар в корзину
	_, err = h.queries.AddItemToCart(c.Request.Context(), repository.AddItemToCartParams{
		CartID: int32(cartID),
		ItemID: int32(itemID),
	})
	if err != nil {
		// Проверяем ошибку foreign key constraint
		if pqErr, ok := err.(*pq.Error); ok {
			if pqErr.Code == "23503" { // foreign_key_violation
				c.JSON(http.StatusNotFound, ErrorResponse{Message: "Cart with id=" + c.Param("cart_id") + " or item with id=" + c.Param("item_id") + " not found"})
				return
			}
		}
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	// Возвращаем обновленную корзину
	cartResponse, err := h.buildCartResponse(c.Request.Context(), int32(cartID))
	if err != nil {
		c.JSON(http.StatusInternalServerError, ErrorResponse{Message: err.Error()})
		return
	}

	c.JSON(http.StatusOK, cartResponse)
}
