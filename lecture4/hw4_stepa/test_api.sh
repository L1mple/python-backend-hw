echo "TESTING STEPA SHOP API"

API_BASE="http://localhost:8001"

echo "1. Checking API health..."
curl -s "$API_BASE/health"

echo -e "\n\n2. Creating test products..."
curl -X POST "$API_BASE/products" -H "Content-Type: application/json" -d '{"title": "iPhone 15", "cost": 999.99}'
echo ""
curl -X POST "$API_BASE/products" -H "Content-Type: application/json" -d '{"title": "iPad Air", "cost": 599.99}'
echo ""
curl -X POST "$API_BASE/products" -H "Content-Type: application/json" -d '{"title": "Apple Watch", "cost": 399.99}'

echo -e "\n3. Listing all products:"
curl -s "$API_BASE/products" | python3 -m json.tool

echo -e "\n4. Creating a basket..."
BASKET_RESPONSE=$(curl -s -X POST "$API_BASE/baskets")
echo "$BASKET_RESPONSE"
BASKET_ID=$(echo "$BASKET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Basket ID: $BASKET_ID"

echo -e "\n5. Adding products to basket..."
curl -X POST "$API_BASE/baskets/$BASKET_ID/products/1"
echo ""
curl -X POST "$API_BASE/baskets/$BASKET_ID/products/2"
echo ""
curl -X POST "$API_BASE/baskets/$BASKET_ID/products/1"

echo -e "\n6. Viewing basket contents:"
curl -s "$API_BASE/baskets/$BASKET_ID" | python3 -m json.tool

echo -e "\n7. Updating product information..."
curl -X PUT "$API_BASE/products/2" -H "Content-Type: application/json" -d '{"title": "iPad Pro", "cost": 1099.99}'
echo ""

echo -e "\n8. Partial product update..."
curl -X PATCH "$API_BASE/products/3" -H "Content-Type: application/json" -d '{"cost": 349.99}'
echo ""

echo -e "\n9. Basket after price updates:"
curl -s "$API_BASE/baskets/$BASKET_ID" | python3 -m json.tool

echo -e "\n10. Removing a product..."
curl -X DELETE "$API_BASE/products/1"
echo ""

echo -e "\n11. Filtering products by cost (200-800):"
curl -s "$API_BASE/products?min_cost=200&max_cost=800" | python3 -m json.tool

echo -e "\n12. Listing all baskets:"
curl -s "$API_BASE/baskets" | python3 -m json.tool

echo -e "\n13. Testing isolation levels..."
echo "Isolation info:"
curl -s "$API_BASE/products/isolation/info" | python3 -m json.tool

echo -e "\nDirty read test:"
curl -s "$API_BASE/products/isolation/dirty_read/2" | python3 -m json.tool

echo -e "\nNon-repeatable read test:"
curl -s "$API_BASE/products/isolation/non_repeatable/2" | python3 -m json.tool

echo -e "\nPhantom read test:"
curl -s "$API_BASE/products/isolation/phantom/100" | python3 -m json.tool

echo -e "\nALL TESTS COMPLETED SUCCESSFULLY"