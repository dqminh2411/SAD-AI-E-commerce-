# Thiết kế Product Service trong hệ thống Microservices E-commerce
## 1. Hướng tiếp cận
- Hệ thống e-commerce này có product service quản lý nhiều loại sản phẩm: Laptop và Clothes

## 2. Folder structure
### 2.1 Nguyên tắc
- Không tách theo category
- Category là dữ liệu
- Structure theo domain

### 2.2 Cấu trúc thư mục
```
product_service/
    manage.py
    config/
        settings/
            base.py
            dev.py
            prod.py
        urls.py
        asgi.py
    modules/
        catalog/
        domain/
            entities/
                product.py # Product core entity
                variant.py # Bin th (size, color)
                category.py #Category tree
                brand.py
                product_type.py
        value_objects/
            money.py
            sku.py
            attributes.py #JSON attributes
        repositories/
            product_repository.py
        application/
            services/
                product_service.py
        commands/
            create_product.py
            update_product.py
            create_variant.py
        queries/
            get_product.py
            list_products.py
            filter_products.py
        
    infrastructure/
        models/
            product_model.py
            category_model.py
            variant_model.py
            brand_model.py
            product_type_model.py
        repositories/
            product_repository_impl.py
        querysets/
            product_queryset.py
        migrations/
    presentation/
        api/
            views/
                product_view.py
                category_view.py
        serializers/
            product_serializer.py
            category_serializer.py

            urls.py
        admin.py
    seeds/
        categories_seed.py
        products_seed.py
    tests/
        test_product.py
        test_category.py

    shared/
        database/
        exceptions/
        utils/

docker-compose.yml
```
## 3. Giải thích
- Domain: logic thuần, không phụ thuộc framework
- Application: xử lý usecase 
- Infrastructure: ORM, database
- Presentation: API

## 4. Database design
- products table:  id serial, name text, category_id int, price numeric, attributes jsonb, created_at timestamp, updated_at timestamp 

## 5. Workflow
1. User request product
2. Product Service trả dữ liệu
3. Cart lưu product_id
4. Order xử lý thanh toán

## 6. API & DTO (phục vụ workflow)
- Thiết kế endpoints + DTO chi tiết: xem `entity_and_db_design.md` (mục 7 và 8)
- Tối thiểu cần:
    - `GET /api/v1/products` (list/search)
    - `GET /api/v1/products/{product_id}` (detail)
    - `POST /api/v1/products/lookup` (Cart/Order validate id + lấy giá/tồn kho)
