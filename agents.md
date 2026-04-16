# Simple microservice e-commerce website
## 1. Features
- Customer registration and authentication
- Product listing and search: laptops and clothes
- Shopping cart and checkout
- Staff management: login, add/edit/delete products, view orders
## 2. Service decomposition
- customer Service: handles user registration, authentication, and profile management
- laptop service: manages laptop product information, catalog and inventory
- cart service: manages shopping cart operations and checkout process
- staff service: handles staff authentication and product 
management
- clothes service: manages clothes product information, catalog and inventory
- an api gateway to route requests to appropriate services and handle html rendering for the frontend (can use Django for this) (templates are divided into folder: products, staff, customer, cart)
## 3. database 
- customer and staff service: use mysql
- cart, laptop and clothes service: use postgresql (use fulltext + substring search for product search)
## 4. Technology stack
- Django REST Framework
- REST inter-service calls
- Docker Compose
- Independent databases
## 5. requirements:
- models in same service can have foreign key relationship, but no cross-service foreign key relationship (use IDs instead)
- create sql scripts to create tables and sample data for these services
    - some sample laptop image urls (each image url for a laptop product):
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:0:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/t/e/text_ng_n_4__9_56.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:300:300/q:100/plain/https://cellphones.com.vn/media/catalog/product/m/a/macbook_13_17.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:300:300/q:100/plain/https://cellphones.com.vn/media/catalog/product/t/e/text_d_i_7_36.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/g/r/group_843.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/g/r/group_659_1__4.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/g/r/group_744_1_15.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/g/r/group_744_1_96.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/g/r/group_906_1_.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/m/a/macbook_9__4.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/t/e/text_ng_n_2__13_50.png
        - https://cdn2.cellphones.com.vn/insecure/rs:fill:358:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/t/e/text_ng_n_2__13_86.png
    - some clothes image urls (each image url for a clothes product):
        - polo shirt: https://n7media.coolmate.me/uploads/2026/03/19/ao-polo-nam-pbc-exdry-proactive-world-cup-_17-vang.jpg?aio=w-700
        - sports polo: https://n7media.coolmate.me/uploads/2026/01/08/ao-polo-the-thao-nam-quick-dry-active-4-xam_85.jpg?aio=w-700
        - sơ mi nam: https://n7media.coolmate.me/uploads/September2025/ao-so-mi-overshirt-100-cotton-den-2_51.jpg?aio=w-700
        - sơ mi dài tay: https://n7media.coolmate.me/uploads/September2025/ao-so-mi-nam-dai-tay-cafe-dris-khu-mui-xanh-aqua-2.jpg?aio=w-700
        - sơ mi flannel: https://n7media.coolmate.me/uploads/September2025/ao-so-mi-flannel-100-cotton-be-vang-2_93.jpg?aio=w-700
        - sơ mi oxford: https://n7media.coolmate.me/uploads/September2025/ao-so-mi-nam-dai-tay-oxford-premium-xanh-dark-blue-2_50.jpg?aio=w-700
- each service has it own dockerfile, dockerignore, requirements.txt
- use pymysql for mysql connection and add this code to __init__.py of customer and staff service:
    ```python
    import pymysql

    pymysql.version_info = (2, 2, 1, 'final', 0)

    pymysql.install_as_MySQLdb()
    ```
- not map mysql db to port 3306, not map postgresql db to port 5432 in docker compose, use custom ports instead (e.g. 3307 for mysql, 5433 for postgresql)
- UI modern, user-friendly, not flashy, banner on homepage, product listing page with pagination, product detail page, shopping cart page, staff dashboard for product management and order viewing, authentication pages for customers and staff
- implement search functionality for products in product service using fulltext + substring search in postgresql (filter by product_type: LAPTOP/CLOTHES)
- for each service create project via django-admin startproject, create app via python manage.py startapp, define models, serializers, views and urls for the service, implement inter-service communication using requests library for REST API calls, handle authentication and authorization for customers and staff, implement frontend templates using Django's template system, use Docker Compose to containerize the services and databases, write SQL scripts to create tables and insert sample data for each service.
for example, for customer service:
```
django-admin startproject customer_service
cd customer_service
python manage.py startapp customer
```
Then define models in customer/models.py, serializers in customer/serializers.py, views in customer/views.py, urls in customer/urls.py, and templates in api gateway project. Repeat similar steps for other services.
- so there are 6 django projects in total: customer_service, product_service, cart_service, staff_service, api_gateway and ai_chat_service. Each project has its own Dockerfile, dockerignore, requirements.txt and database setup. The api_gateway project will handle routing requests to appropriate services and rendering HTML templates for the frontend. 
- use the right service name

## Todo (26/3/2026):
- create clothes service using postgresql with all feature like laptop service

    - some clothes image urls:
        - polo shirt: https://n7media.coolmate.me/uploads/2026/03/19/ao-polo-nam-pbc-exdry-proactive-world-cup-_17-vang.jpg?aio=w-700
        - sports polo: https://n7media.coolmate.me/uploads/2026/01/08/ao-polo-the-thao-nam-quick-dry-active-4-xam_85.jpg?aio=w-700
        - sơ mi nam: https://n7media.coolmate.me/uploads/September2025/ao-so-mi-overshirt-100-cotton-den-2_51.jpg?aio=w-700
        - sơ mi dài tay: https://n7media.coolmate.me/uploads/September2025/ao-so-mi-nam-dai-tay-cafe-dris-khu-mui-xanh-aqua-2.jpg?aio=w-700
        - sơ mi flannel: https://n7media.coolmate.me/uploads/September2025/ao-so-mi-flannel-100-cotton-be-vang-2_93.jpg?aio=w-700
        - sơ mi oxford: https://n7media.coolmate.me/uploads/September2025/ao-so-mi-nam-dai-tay-oxford-premium-xanh-dark-blue-2_50.jpg?aio=w-700
- no longer use mysql for cart service, use postgresql instead, update docker compose and code accordingly
- remove smartphone service, now my shop only sells laptops and clothes, update docker compose and code accordingly
- about fulltext search, i also want to search with substring as well, for example if i search "mac", it should return macbook products, if i search "pro", it should return macbook pro products, if i search "air", it should return macbook air products, not only when i search "macbook pro" it returns macbook pro products. So implement fulltext search with substring matching in laptop service and clothes service.
- update the shop UI (both customer and staff) like the images provided in chat. the current UI is too basic, i want it to look more modern, attractive and user-friendly with a nice banner on homepage. 

## fix 1 (26/3/2026):
- i prefer staff to have a separate login page, dashboard page: tabs product including laptops, clothes, add/edit/delete product, and tab orders to view orders. so update staff service and api gateway accordingly. The header shouldn't share with customer
- about search functionality, I want to use ":*" and "&" operator in postgresql to implement FTS with substring matching
- sometimes, mysql db is ready to receive connection after the service container is ready, so add command to run migrations before starting the server in customer and staff service in docker compose file to avoid connection error when the service tries to connect to mysql db before it's ready.

## fix 2 (26/3/2026):
- not use a button to switch between user and staff login, instead, have separate login pages for customer and staff, update api gateway and staff service accordingly. The header for staff pages shouldn't be the same as customer pages, it should be more admin-like with links to product management and order viewing pages.
- for product management, separate UI for laptop and clothes as:
    - laptop must have more infomation like technical specifications: processor, gpu, ram, storage, screen size, battery life, weight, release date, connectivity, etc.. and also have image urls for each laptop product
    - clothes must have more infomation like size, material, color
    - staff can import products (select or search for already created product and add quantity), not just create and edit 
    - update customer UI, staff UI and functionality for these requirements
- in customer UI, there are two tabs and default tab is laptop. home pages should show laptop products by default, and customer can switch to clothes tab to view clothes products. also update search functionality to search in the current selected tab (laptop or clothes). In clothes tab, there is a banner, image url for banner: https://n7media.coolmate.me/uploads/2026/03/23/gateway_banner_nam_7th.jpg?aio=w-1069.
