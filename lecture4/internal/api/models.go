package api

// ItemRequest представляет запрос на создание или обновление товара
type ItemRequest struct {
	Name  string  `json:"name" binding:"required" example:"Молоко"`
	Price float64 `json:"price" binding:"required,gte=0" example:"159.99"`
}

// PatchItemRequest представляет запрос на частичное обновление товара
type PatchItemRequest struct {
	Name  *string  `json:"name,omitempty" example:"Молоко обновленное"`
	Price *float64 `json:"price,omitempty" example:"169.99"`
}

// ItemResponse представляет ответ с информацией о товаре
type ItemResponse struct {
	ID      int32   `json:"id" example:"1"`
	Name    string  `json:"name" example:"Молоко"`
	Price   float64 `json:"price" example:"159.99"`
	Deleted bool    `json:"deleted" example:"false"`
}

// CartItemResponse представляет товар в корзине
type CartItemResponse struct {
	ID        int32  `json:"id" example:"1"`
	Name      string `json:"name" example:"Молоко"`
	Quantity  int32  `json:"quantity" example:"3"`
	Available bool   `json:"available" example:"true"`
}

// CartResponse представляет ответ с информацией о корзине
type CartResponse struct {
	ID    int32              `json:"id" example:"1"`
	Items []CartItemResponse `json:"items"`
	Price float64            `json:"price" example:"234.40"`
}

// CartIdResponse представляет ответ с ID корзины
type CartIdResponse struct {
	ID int32 `json:"id" example:"1"`
}

// ErrorResponse представляет ответ с ошибкой
type ErrorResponse struct {
	Message string `json:"detail" example:"Item not found"`
}
