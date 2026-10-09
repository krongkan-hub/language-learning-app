// Which backdrop each of the 80 scenarios gets. A dozen templates, each with
// a wall colour, the goods on its shelves and the sign over the counter in
// both languages — so 80 places come out of a small drawing vocabulary.

export type Template =
  | 'counter' | 'desk' | 'transit' | 'office' | 'market' | 'road' | 'gallery'
  | 'workshop' | 'home' | 'outdoors' | 'boxoffice' | 'harbor' | 'kitchen'

export type Goods =
  | 'cups' | 'bread' | 'books' | 'bottles' | 'flowers' | 'icecream' | 'boxes' | 'clothes'
  | 'guitars' | 'tools' | 'screens' | 'frames' | 'phones' | 'plants' | 'shoes' | 'fabric'
  | 'garments' | 'medicine' | 'souvenirs' | 'cosmetics' | 'produce' | 'food' | 'wine'
  | 'bikes' | 'skis' | 'none'

export type Wall = 'warm' | 'cool' | 'mint' | 'blush' | 'lavender' | 'grey' | 'night' | 'sky'

export interface SceneSpec {
  template: Template
  wall: Wall
  goods: Goods
  sign: [string, string]          // [English, Japanese]
  variant?: string                // template-specific: 'plane' | 'snow' | 'night' | ...
}

const S = (template: Template, wall: Wall, goods: Goods, en: string, ja: string, variant?: string): SceneSpec =>
  ({ template, wall, goods, sign: [en, ja], variant })

export const SCENES: Record<string, SceneSpec> = {
  'Fine Dining Restaurant': S('counter', 'night', 'wine', 'RESTAURANT', 'レストラン', 'dining'),
  'Airport Check-in & Security': S('transit', 'cool', 'none', 'DEPARTURES', '出発', 'plane'),
  'Coffee Shop': S('counter', 'warm', 'cups', 'COFFEE', 'カフェ'),
  'Pharmacy': S('counter', 'mint', 'medicine', 'PHARMACY', '薬局'),
  'Hotel Check-in': S('desk', 'warm', 'none', 'RECEPTION', 'フロント', 'hotel'),
  'Customs Clearance': S('transit', 'grey', 'none', 'CUSTOMS', '税関', 'customs'),
  'Car Rental Agency': S('transit', 'cool', 'none', 'CAR RENTAL', 'レンタカー', 'car'),
  'Clothing Store Shopping': S('counter', 'blush', 'clothes', 'BOUTIQUE', 'ブティック'),
  'Train Station Ticket Counter': S('transit', 'cool', 'none', 'TICKETS', 'きっぷ売り場', 'train'),
  'Hospital Clinic Check-in': S('desk', 'mint', 'none', 'OUTPATIENTS', '外来受付', 'clinic'),
  'Bank Account Opening': S('desk', 'cool', 'none', 'BANK', '銀行', 'bank'),
  'Apartment Rental Inspection': S('home', 'warm', 'none', '1LDK', '1LDK', 'empty'),
  'Tech Support Repair Shop': S('workshop', 'cool', 'phones', 'REPAIRS', '修理受付', 'bench'),
  'Bookstore Recommendation': S('counter', 'warm', 'books', 'BOOKS', '本屋'),
  'Hair Salon Barber': S('desk', 'blush', 'none', 'SALON', '美容院', 'salon'),
  'Gym Membership Inquiry': S('desk', 'grey', 'none', 'FITNESS', 'フィットネス', 'gym'),
  'Job Interview (Software Engineer)': S('office', 'cool', 'none', 'MEETING ROOM', '会議室', 'startup'),
  'Job Interview (Marketing)': S('office', 'blush', 'none', 'MARKETING', 'マーケティング部', 'chart'),
  'Taxi Ride Share Driver': S('road', 'sky', 'none', 'TAXI', 'タクシー', 'car'),
  'Museum Tour Guide': S('gallery', 'warm', 'none', 'MUSEUM', '博物館', 'museum'),
  'Farmers Market Stall': S('market', 'sky', 'produce', 'FRESH', '青空市場'),
  'Pet Clinic Vet': S('desk', 'mint', 'none', 'VET CLINIC', '動物病院', 'vet'),
  'Bakery Pastry Shop': S('counter', 'warm', 'bread', 'BAKERY', 'パン屋'),
  'Post Office Parcel Shipping': S('counter', 'cool', 'boxes', 'POST OFFICE', '郵便局'),
  'Bike Rental Shop': S('outdoors', 'sky', 'bikes', 'BIKE RENTAL', 'レンタサイクル', 'beach'),
  'Cinema Ticket Counter': S('boxoffice', 'night', 'none', 'CINEMA', '映画館', 'cinema'),
  'Dry Cleaners Pickup': S('counter', 'cool', 'garments', 'CLEANERS', 'クリーニング'),
  'Police Station Lost Property': S('desk', 'grey', 'none', 'POLICE', '警察署', 'police'),
  'Tourist Info Center': S('desk', 'sky', 'none', 'INFORMATION', '観光案内所', 'info'),
  'Souvenir Shop Bargaining': S('counter', 'warm', 'souvenirs', 'SOUVENIRS', 'おみやげ'),
  'Mobile Phone Plan Sign-up': S('counter', 'cool', 'phones', 'MOBILE', 'ケータイ'),
  'Furniture Store Buying Sofa': S('home', 'warm', 'none', 'SHOWROOM', 'ショールーム', 'showroom'),
  'Hardware Store Supplies': S('workshop', 'warm', 'tools', 'HARDWARE', 'ホームセンター', 'store'),
  'Spa & Massage Reservation': S('desk', 'mint', 'none', 'SPA', 'スパ', 'spa'),
  'University Admissions Office': S('desk', 'cool', 'none', 'STUDENT SERVICES', '学生センター', 'office'),
  'Library Card Registration': S('counter', 'warm', 'books', 'LIBRARY', '図書館', 'quiet'),
  'Music Instrument Store': S('counter', 'warm', 'guitars', 'MUSIC', '楽器店'),
  'Flower Shop Bouquet': S('counter', 'blush', 'flowers', 'FLOWERS', '花屋'),
  'Ice Cream Parlor': S('counter', 'blush', 'icecream', 'ICE CREAM', 'アイスクリーム'),
  'Fast Food Drive-thru': S('road', 'sky', 'none', 'DRIVE-THRU', 'ドライブスルー', 'drive'),
  'Wine Tasting Tour': S('outdoors', 'sky', 'wine', 'TASTING ROOM', '試飲室', 'vineyard'),
  'Ski Resort Pass & Gear': S('outdoors', 'sky', 'skis', 'SKI RENTAL', 'スキーレンタル', 'snow'),
  'Amusement Park Tickets': S('boxoffice', 'sky', 'none', 'TICKETS', '入場券', 'park'),
  'Camping Ground Desk': S('outdoors', 'sky', 'none', 'CAMPGROUND', 'キャンプ場', 'forest'),
  'Art Gallery Inquiry': S('gallery', 'grey', 'none', 'GALLERY', 'ギャラリー', 'modern'),
  'Tailor Suit Fitting': S('counter', 'warm', 'fabric', 'TAILOR', 'テーラー'),
  'Electronics Store TV Buying': S('counter', 'cool', 'screens', 'ELECTRONICS', '家電'),
  'Insurance Policy Review': S('office', 'cool', 'none', 'INSURANCE', '保険', 'desk'),
  'Real Estate House Tour': S('home', 'warm', 'none', 'FOR SALE', '売り家', 'house'),
  'Auto Repair Mechanic': S('workshop', 'grey', 'tools', 'GARAGE', '修理工場', 'garage'),
  'Dental Clinic Checkup': S('desk', 'mint', 'none', 'DENTAL', '歯科', 'clinic'),
  'Optician Eyeglasses': S('counter', 'cool', 'frames', 'OPTICIAN', '眼鏡店'),
  'Public Bus Info Desk': S('transit', 'cool', 'none', 'BUS TERMINAL', 'バスターミナル', 'bus'),
  'Ferry Terminal Booking': S('harbor', 'sky', 'none', 'FERRY', 'フェリー', 'ferry'),
  'Bowling Alley Booking': S('boxoffice', 'night', 'none', 'BOWLING', 'ボウリング', 'bowling'),
  'Escape Room Desk': S('boxoffice', 'night', 'none', 'ESCAPE ROOM', '脱出ゲーム', 'escape'),
  'Karaoke Room Rental': S('boxoffice', 'night', 'none', 'KARAOKE', 'カラオケ', 'karaoke'),
  'Tattoo Parlor Consultation': S('gallery', 'night', 'none', 'TATTOO', 'タトゥー', 'flash'),
  'Flea Market Antiques': S('market', 'sky', 'souvenirs', 'ANTIQUES', '骨董市'),
  'Street Food Night Market': S('market', 'night', 'food', 'NIGHT MARKET', '夜市', 'night'),
  'Cooking Class Registration': S('kitchen', 'warm', 'none', 'COOKING CLASS', '料理教室'),
  'Yoga Studio Class Pass': S('desk', 'mint', 'none', 'YOGA', 'ヨガ', 'spa'),
  'Music Concert Box Office': S('boxoffice', 'night', 'none', 'LIVE TONIGHT', '本日公演', 'concert'),
  'Airport Duty Free Shop': S('counter', 'lavender', 'cosmetics', 'DUTY FREE', '免税店'),
  'Shoe Repair Shop': S('workshop', 'warm', 'shoes', 'SHOE REPAIR', '靴修理', 'bench'),
  'Public Swimming Pool Pass': S('desk', 'sky', 'none', 'SPORTS CENTRE', 'スポーツセンター', 'pool'),
  'Plant Nursery Advice': S('market', 'sky', 'plants', 'GARDEN CENTRE', '園芸店', 'greenhouse'),
  'Airport Lounge Access': S('desk', 'lavender', 'none', 'LOUNGE', 'ラウンジ', 'lounge'),
  'Co-working Space Hot Desk': S('office', 'warm', 'none', 'CO-WORKING', 'コワーキング', 'cowork'),
  'Apartment Neighbor Conversation': S('home', 'warm', 'none', '302', '302', 'hallway'),
  'Emergency Room Triage Desk': S('desk', 'mint', 'none', 'EMERGENCY', '救急受付', 'er'),
  'Flight Delay & Ticket Cancellation Desk': S('transit', 'grey', 'none', 'DELAYED', '遅延', 'storm'),
  'Insurance Claim Dispute Call': S('office', 'grey', 'none', 'CLAIMS', '保険金請求', 'desk'),
  'Tech Startup Co-Founder Equity & Role Alignment': S('office', 'warm', 'none', 'MEETING ROOM', '会議室', 'startup'),
  'Traffic Police Roadside Stop': S('road', 'sky', 'none', 'HIGHWAY', '高速道路', 'roadside'),
  'Landlord Maintenance & Rent Escalation Dispute': S('home', 'warm', 'none', 'FLAT 4B', '4B号室', 'lived'),
  'Customs Import Duties & Tariff Hearing': S('harbor', 'grey', 'none', 'PORT CUSTOMS', '税関事務所', 'port'),
  'Executive Performance Review & Promotion Request': S('office', 'cool', 'none', 'MANAGER', '部長室', 'chart'),
  'Bank Loan & Mortgage Officer Meeting': S('office', 'cool', 'none', 'PRIVATE BANKING', '個室相談', 'desk'),
  'Wedding & Event Planner Consultation': S('gallery', 'blush', 'flowers', 'EVENTS', 'イベント', 'wedding'),
}

/** A scenario's backdrop; an unknown one (a new scenario) gets a plain front desk. */
export function sceneFor(scenario: string): SceneSpec {
  return SCENES[scenario] ?? S('desk', 'cool', 'none', '', '')
}
