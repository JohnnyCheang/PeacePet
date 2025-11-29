import os
import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, g, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.secret_key = 'peacepet_luxury_cms_secret_key_change_me' 

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 1. 扩充字体选项 (Issue 2)
FONT_OPTIONS = [
    'Playfair Display', 'Lato', 'Arial', 'Helvetica', 'Georgia', 'Verdana', 
    'Times New Roman', 'Courier New', 'Montserrat', 'Roboto', 'Open Sans', 
    'Garamond', 'Palatino', 'Bookman', 'Trebuchet MS'
]

@app.context_processor
def inject_common():
    return {'FONT_OPTIONS': FONT_OPTIONS, 'now': datetime.now}

def get_db_conn():
    conn = sqlite3.connect('peacepet.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, name_en TEXT, name_zh TEXT, slug TEXT UNIQUE, image TEXT, sort_order INTEGER DEFAULT 0)''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            category_id INTEGER, 
            title_en TEXT, title_zh TEXT, 
            price TEXT, main_image TEXT, 
            bullet_points_en TEXT, bullet_points_zh TEXT, 
            description_en TEXT, description_zh TEXT, 
            a_plus_images TEXT, 
            is_new INTEGER DEFAULT 0, is_deal INTEGER DEFAULT 0, is_featured INTEGER DEFAULT 0, 
            monthly_sales INTEGER DEFAULT 0, avg_rating REAL DEFAULT 5.0
        )
    ''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, product_id INTEGER, rating REAL, text_en TEXT, text_zh TEXT, image TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, product_name TEXT, customer_name TEXT, contact_info TEXT, note TEXT, date TEXT)''')
    
    try: c.execute("ALTER TABLE products ADD COLUMN is_featured INTEGER DEFAULT 0")
    except: pass
    try: c.execute("ALTER TABLE feedback ADD COLUMN category_id INTEGER DEFAULT 0")
    except: pass
        
    # 默认设置初始化 (包含所有板块的字体设置)
    defaults = {
        'site_logo': '', 'contact_email': 'support@peacepet.com',
        'footer_text_en': 'Designed by professional trainers.', 'footer_text_zh': '专业训犬师设计。',
        
        # 首页 Banner
        'hero_banner_type': 'url', 
        'hero_banner_url': 'https://images.unsplash.com/photo-1583511655857-d19b40a7a54e',
        'hero_banner_upload': '', 
        'hero_title_en': 'The Art of Protection', 'hero_title_zh': '守护的艺术',
        'hero_slogan_en': 'PROFESSIONAL GRADE GEAR', 'hero_slogan_zh': '现代爱犬的专业级装备',
        'hero_title_size': '3.5', 'hero_title_font': 'Playfair Display',
        'hero_slogan_size': '1.2', 'hero_slogan_font': 'Lato', 
        
        # 首页 Slogan Block
        'home_slogan_img': '', 
        'home_slogan_title_en': 'Our Mission', 'home_slogan_title_zh': '我们的使命',
        'home_slogan_body_en': 'We strive to provide premium gear.', 'home_slogan_body_zh': '我们致力于提供优质装备。',
        'home_slogan_title_size': '2.0', 'home_slogan_title_font': 'Playfair Display',
        'home_slogan_body_size': '1.1', 'home_slogan_body_font': 'Lato',
        
        # Deals Page
        'deals_title_en': 'Exclusive Deals', 'deals_title_zh': '独家优惠',
        'deals_body_en': 'Limited time offers and discounts!', 'deals_body_zh': '限时优惠和折扣！',
        'deals_banner_upload': '', 'deals_banner_link': '/',
        'deals_title_font': 'Playfair Display', 'deals_title_size': '3.0',
        'deals_body_font': 'Lato', 'deals_body_size': '1.2',
        
        # New Arrivals Page
        'new_title_en': 'New Arrivals', 'new_title_zh': '新品到货',
        'new_body_en': 'The latest products have arrived.', 'new_body_zh': '最新产品已到货。',
        'new_banner_upload': '', 'new_banner_link': '/',
        'new_title_font': 'Playfair Display', 'new_title_size': '3.0',
        'new_body_font': 'Lato', 'new_body_size': '1.2',

        # Catalog Page (新增字体设置)
        'catalog_title_en': 'Product Collection', 'catalog_title_zh': '产品系列',
        'catalog_body_en': 'Discover our premium range.', 'catalog_body_zh': '探索我们的专业系列。',
        'catalog_title_font': 'Playfair Display', 'catalog_title_size': '3.0',
        'catalog_body_font': 'Lato', 'catalog_body_size': '1.2',

        # About Us (3个插槽)
        'about_image_1': '', 'about_caption_1_en': '', 'about_caption_1_zh': '',
        'about_image_2': '', 'about_caption_2_en': '', 'about_caption_2_zh': '',
        'about_image_3': '', 'about_caption_3_en': '', 'about_caption_3_zh': '',
        'about_page_title_en': 'Our Story', 'about_page_title_zh': '品牌故事',
        'about_page_body_en': 'PeacePet story...', 'about_page_body_zh': 'PeacePet 的故事...',
        'about_page_title_font': 'Playfair Display', 'about_page_title_size': '2.5',
        'about_page_body_font': 'Lato', 'about_page_body_size': '1.0',
    }
    for key, val in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (key, val))
    conn.commit()
    conn.close()

init_db()

@app.before_request
def set_language_and_nav():
    if 'lang' not in session: session['lang'] = 'en'
    g.lang = session['lang'] 
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM categories ORDER BY sort_order DESC, id DESC")
    g.categories = c.fetchall()
    c.execute("SELECT * FROM settings")
    g.settings = {row['key']: row['value'] for row in c.fetchall()}
    conn.close()

@app.route('/switch_lang/<new_lang>')
def switch_lang(new_lang):
    if new_lang in ['en', 'zh']: session['lang'] = new_lang
    return redirect(request.referrer or url_for('index'))

# --- 前台路由 ---
@app.route('/')
def index():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE is_featured = 1 ORDER BY id DESC LIMIT 6")
    products = c.fetchall()
    conn.close()
    return render_template('index.html', products=products)

@app.route('/about')
def about(): 
    about_images_data = [
        {'key': 'about_image_1', 'src': g.settings.get('about_image_1'), 'caption_en': g.settings.get('about_caption_1_en'), 'caption_zh': g.settings.get('about_caption_1_zh')},
        {'key': 'about_image_2', 'src': g.settings.get('about_image_2'), 'caption_en': g.settings.get('about_caption_2_en'), 'caption_zh': g.settings.get('about_caption_2_zh')},
        {'key': 'about_image_3', 'src': g.settings.get('about_image_3'), 'caption_en': g.settings.get('about_caption_3_en'), 'caption_zh': g.settings.get('about_caption_3_zh')},
    ]
    return render_template('about.html', about_images_data=about_images_data)

@app.route('/catalog')
def catalog_index(): return render_template('catalog_index.html')

@app.route('/deals')
def deals():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE is_deal = 1 ORDER BY id DESC")
    products = c.fetchall()
    conn.close()
    return render_template('deals.html', products=products)

@app.route('/new_arrivals')
def new_arrivals():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE is_new = 1 ORDER BY id DESC")
    products = c.fetchall()
    conn.close()
    return render_template('new_arrivals.html', products=products)

@app.route('/catalog/<slug>')
def category_detail(slug):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM categories WHERE slug = ?", (slug,))
    category = c.fetchone()
    if not category: abort(404)
    c.execute("SELECT * FROM products WHERE category_id = ? ORDER BY id DESC", (category['id'],))
    products = c.fetchall()
    conn.close()
    return render_template('category_detail.html', products=products, category=category)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    if not product: abort(404)
    c.execute("SELECT * FROM feedback WHERE product_id = ? ORDER BY id DESC", (product_id,))
    reviews = c.fetchall()
    conn.close()
    bullets_field = f"bullet_points_{g.lang}"
    bullets = product[bullets_field].split('\n') if product[bullets_field] else []
    a_plus_imgs = product['a_plus_images'].split(',') if product['a_plus_images'] else []
    return render_template('product.html', product=product, bullets=bullets, a_plus_imgs=a_plus_imgs, reviews=reviews)

@app.route('/submit_order', methods=['POST'])
def submit_order():
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("INSERT INTO orders (product_name, customer_name, contact_info, note, date) VALUES (?, ?, ?, ?, ?)",
              (request.form.get('product_name'), request.form.get('customer_name'), request.form.get('contact'), request.form.get('note', ''), datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return "OK"

# --- 后台管理路由 ---

@app.route('/admin/delete/category/<int:cat_id>')
def delete_category(cat_id):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', tab='categories'))

@app.route('/admin/delete/product/<int:product_id>')
def delete_product(product_id):
    conn = get_db_conn()
    c = conn.cursor()
    c.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin', tab='products'))

@app.route('/admin/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_conn()
    c = conn.cursor()
    if request.method == 'POST':
        product_data = c.execute("SELECT main_image, a_plus_images FROM products WHERE id = ?", (product_id,)).fetchone()
        main_img = request.files.get('main_image')
        main_filename = product_data['main_image']
        if main_img and main_img.filename:
            main_filename = "main_" + secure_filename(main_img.filename)
            main_img.save(os.path.join(app.config['UPLOAD_FOLDER'], main_filename))
        
        a_plus_files = request.files.getlist('a_plus_images')
        a_plus_filenames = []
        for file in a_plus_files:
            if file and file.filename:
                fname = "aplus_" + secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], fname))
                a_plus_filenames.append(fname)
        a_plus_str = ",".join(a_plus_filenames) if a_plus_filenames else product_data['a_plus_images']

        c.execute("""UPDATE products SET category_id=?, title_en=?, title_zh=?, price=?, main_image=?, bullet_points_en=?, bullet_points_zh=?, description_en=?, description_zh=?, a_plus_images=?, monthly_sales=?, avg_rating=?, is_new=?, is_deal=?, is_featured=? WHERE id=?""", 
            (
                request.form.get('category_id'), 
                request.form.get('title_en'), 
                request.form.get('title_zh'), 
                request.form.get('price'), 
                main_filename, 
                request.form.get('bullet_points_en', ''), 
                request.form.get('bullet_points_zh', ''), 
                request.form.get('description_en', ''), 
                request.form.get('description_zh', ''), 
                a_plus_str, 
                request.form.get('monthly_sales', 0), 
                request.form.get('avg_rating', 5.0), 
                1 if request.form.get('is_new')=='on' else 0, 
                1 if request.form.get('is_deal')=='on' else 0, 
                1 if request.form.get('is_featured')=='on' else 0, 
                product_id
            ))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    product = c.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    categories_list = c.execute("SELECT id, name_zh, name_en FROM categories").fetchall()
    conn.close()
    a_plus_imgs = product['a_plus_images'].split(',') if product['a_plus_images'] else []
    return render_template('edit_product.html', product=product, categories_list=categories_list, a_plus_imgs=a_plus_imgs)

@app.route('/admin/edit_category/<int:cat_id>', methods=['GET', 'POST'])
def edit_category(cat_id):
    conn = get_db_conn()
    c = conn.cursor()
    category = c.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
    if request.method == 'POST':
        cat_img = request.files.get('category_image')
        cat_filename = category['image']
        if request.form.get('delete_image') == 'on': cat_filename = "" 
        elif cat_img and cat_img.filename:
            cat_filename = "cat_" + secure_filename(cat_img.filename)
            cat_img.save(os.path.join(app.config['UPLOAD_FOLDER'], cat_filename))
        c.execute("UPDATE categories SET name_en=?, name_zh=?, slug=?, image=?, sort_order=? WHERE id=?", 
                  (request.form.get('name_en'), request.form.get('name_zh'), request.form.get('slug', '').lower().replace(' ', '-'), cat_filename, request.form.get('sort_order', 0), cat_id))
        conn.commit()
        conn.close()
        return redirect(url_for('admin', tab='categories'))
    conn.close()
    return render_template('edit_category.html', category=category)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = get_db_conn()
    c = conn.cursor()

    def handle_single_upload(file_key, setting_key, delete_key, prefix):
        if request.form.get(delete_key) == 'on':
            c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (setting_key, '')) 
        else:
            img_file = request.files.get(file_key)
            if img_file and img_file.filename:
                img_filename = prefix + "_" + secure_filename(img_file.filename)
                img_file.save(os.path.join(app.config['UPLOAD_FOLDER'], img_filename))
                c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (setting_key, img_filename))

    if request.method == 'POST':
        action = request.form.get('admin_action')
        
        if action == 'UPDATE_SETTINGS':
            handle_single_upload('site_logo_file', 'site_logo', 'delete_logo', 'logo')
            
            banner_type = request.form.get('hero_banner_type')
            c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", ('hero_banner_type', banner_type))
            if banner_type == 'url':
                c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", ('hero_banner_url', request.form.get('hero_banner_url', '')))
            else:
                handle_single_upload('hero_banner_upload_file', 'hero_banner_upload', 'delete_hero_banner_upload', 'hero')
            
            handle_single_upload('home_slogan_image_file', 'home_slogan_img', 'delete_home_slogan_image', 'home_slogan')
            handle_single_upload('deals_banner_file', 'deals_banner_upload', 'delete_deals_banner', 'deals_banner')
            handle_single_upload('new_banner_file', 'new_banner_upload', 'delete_new_banner', 'new_banner')

            for i in range(1, 4):
                handle_single_upload(f'about_image_{i}_file', f'about_image_{i}', f'delete_about_image_{i}', f'about_{i}')

            # 排除文件字段，保存所有文本字段 (包括新增加的字体设置)
            excluded = ['admin_action', 'csrf_token', 'site_logo_file', 'delete_logo', 'hero_banner_upload_file', 'delete_hero_banner_upload', 'home_slogan_image_file', 'delete_home_slogan_image', 'deals_banner_file', 'delete_deals_banner', 'new_banner_file', 'delete_new_banner', 'about_image_1_file', 'delete_about_image_1', 'about_image_2_file', 'delete_about_image_2', 'about_image_3_file', 'delete_about_image_3', 'hero_banner_url', 'hero_banner_type']
            
            for key, value in request.form.items():
                if key not in excluded:
                    c.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
            
            conn.commit()
            return redirect(url_for('admin', tab='settings'))

        elif action == 'ADD_PRODUCT':
            # ... (与上面edit_product类似)
            main_img = request.files.get('main_image')
            main_filename = ""
            if main_img and main_img.filename:
                main_filename = secure_filename(main_img.filename)
                main_img.save(os.path.join(app.config['UPLOAD_FOLDER'], "main_" + main_filename))
                main_filename = "main_" + main_filename
            a_plus_files = request.files.getlist('a_plus_images')
            a_plus_filenames = []
            for file in a_plus_files:
                if file and file.filename:
                    fname = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], "aplus_" + fname))
                    a_plus_filenames.append("aplus_" + fname)
            a_plus_str = ",".join(a_plus_filenames)
            c.execute("""INSERT INTO products (category_id, title_en, title_zh, price, main_image, bullet_points_en, bullet_points_zh, description_en, description_zh, a_plus_images, monthly_sales, avg_rating, is_new, is_deal, is_featured) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", 
            (
                request.form.get('category_id'), 
                request.form.get('title_en'), 
                request.form.get('title_zh'), 
                request.form.get('price'), 
                main_filename, 
                request.form.get('bullet_points_en', ''), 
                request.form.get('bullet_points_zh', ''), 
                request.form.get('description_en', ''), 
                request.form.get('description_zh', ''), 
                a_plus_str, 
                request.form.get('monthly_sales', 0), 
                request.form.get('avg_rating', 5.0), 
                1 if request.form.get('is_new')=='on' else 0, 
                1 if request.form.get('is_deal')=='on' else 0, 
                1 if request.form.get('is_featured')=='on' else 0
            ))
            conn.commit()
            return redirect(url_for('admin', tab='products'))
        
        elif action == 'ADD_CATEGORY':
            cat_img = request.files.get('category_image')
            cat_filename = ""
            if cat_img and cat_img.filename:
                cat_filename = secure_filename(cat_img.filename)
                cat_img.save(os.path.join(app.config['UPLOAD_FOLDER'], "cat_" + cat_filename))
                cat_filename = "cat_" + cat_filename
            c.execute("INSERT INTO categories (name_en, name_zh, slug, image, sort_order) VALUES (?, ?, ?, ?, ?)",
                      (request.form.get('name_en'), request.form.get('name_zh'), request.form.get('slug', '').lower().replace(' ', '-'), cat_filename, request.form.get('sort_order', 0)))
            conn.commit()
            return redirect(url_for('admin', tab='categories'))
        
        elif action == 'ADD_FEEDBACK':
            feedback_img = request.files.get('feedback_image')
            img_filename = ""
            if feedback_img and feedback_img.filename:
                img_filename = secure_filename(feedback_img.filename)
                feedback_img.save(os.path.join(app.config['UPLOAD_FOLDER'], "fb_" + img_filename))
                img_filename = "fb_" + img_filename
            c.execute("INSERT INTO feedback (product_id, rating, text_en, text_zh, image) VALUES (?, ?, ?, ?, ?)",
                      (
                          request.form.get('product_id'), 
                          request.form.get('rating', 5.0), 
                          request.form.get('text_en', ''), 
                          request.form.get('text_zh', ''), 
                          img_filename
                      ))
            conn.commit()
            return redirect(url_for('admin', tab='feedback'))
    
    c.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = c.fetchall()
    c.execute("SELECT * FROM categories ORDER BY sort_order DESC, id DESC")
    categories_list = c.fetchall()
    c.execute("SELECT p.*, c.name_zh as category_name_zh, c.name_en as category_name_en FROM products p LEFT JOIN categories c ON p.category_id = c.id ORDER BY p.id DESC")
    products_list = c.fetchall()
    
    about_images_data = [
        {'key': f'about_image_{i}', 'src': g.settings.get(f'about_image_{i}'), 'caption_en': g.settings.get(f'about_caption_{i}_en'), 'caption_zh': g.settings.get(f'about_caption_{i}_zh')}
        for i in range(1, 4)
    ]

    active_tab = request.args.get('tab', 'products')
    conn.close()
    return render_template('admin.html', orders=orders, categories_list=categories_list, products_list=products_list, categories=g.categories, settings_dict=g.settings, about_images_data=about_images_data, active_tab=active_tab)

if __name__ == '__main__':
    init_db() 
    app.run(debug=True, port=5000)