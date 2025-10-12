package main

import (
	"database/sql"
	"log"
	"time"

	"github.com/gin-gonic/gin"
	_ "github.com/lib/pq"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
	"shop-api/internal/api"
	"shop-api/internal/config"

	_ "shop-api/docs"
)

// @title Shop API
// @version 1.0
// @description REST API для интернет магазина с товарами и корзинами
// @host localhost:8080
// @BasePath /
func main() {
	cfg := config.Load()

	// Подключение к базе данных с retry логикой
	var db *sql.DB
	var err error
	for i := 0; i < 10; i++ {
		db, err = sql.Open("postgres", cfg.DatabaseURL)
		if err == nil {
			err = db.Ping()
			if err == nil {
				break
			}
		}
		log.Printf("Failed to connect to database, retrying in 2 seconds... (%d/10)", i+1)
		time.Sleep(2 * time.Second)
	}
	if err != nil {
		log.Fatalf("Failed to connect to database after 10 attempts: %v", err)
	}
	defer db.Close()

	log.Println("Successfully connected to database")

	router := gin.Default()

	router.GET("/metrics", gin.WrapH(promhttp.Handler()))

	router.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

	handler := api.NewHandler(db)

	router.POST("/item", handler.PostItem)
	router.GET("/item/:id", handler.GetItemByID)
	router.GET("/item", handler.GetItems)
	router.PUT("/item/:id", handler.PutItem)
	router.PATCH("/item/:id", handler.PatchItem)
	router.DELETE("/item/:id", handler.DeleteItem)

	router.POST("/cart", handler.PostCart)
	router.GET("/cart/:id", handler.GetCartByID)
	router.GET("/cart", handler.GetCarts)
	router.POST("/cart/:cart_id/add/:item_id", handler.AddItemToCart)

	log.Printf("Starting server on port %s", cfg.Port)
	if err := router.Run(":" + cfg.Port); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
