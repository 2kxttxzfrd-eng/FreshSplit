import streamlit as st
import uuid
import time
import json
import os
from datetime import datetime, date

# --- Persistent Storage ---
DB_FILE = "freshsplit_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'users': {}, 'groups': [], 'shared_items': []}

def save_db(data):
    def json_serial(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, default=json_serial, indent=4)

# --- 1. State Management (Mock Database) ---
# Always load fresh data from DB on script rerun to ensure sync between users
db_data = load_db()
st.session_state.users = db_data.get('users', {})
st.session_state.groups = db_data.get('groups', [])
st.session_state.shared_items = db_data.get('shared_items', [])

if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'draft_items' not in st.session_state:
    st.session_state.draft_items = [] # List of dicts for batch upload

# --- 2. Helper Functions ---
def get_current_db_state():
    return {
        'users': st.session_state.users,
        'groups': st.session_state.groups,
        'shared_items': st.session_state.shared_items
    }

def login(name):
    user_id = str(uuid.uuid4())[:8]
    # Update state
    st.session_state.users[user_id] = name
    st.session_state.current_user = {'id': user_id, 'name': name}
    # Persist
    save_db(get_current_db_state())
    st.rerun()

def create_group(name):
    new_group = {
        'id': str(uuid.uuid4())[:8],
        'name': name,
        'invite_code': str(uuid.uuid4())[:6].upper(),
        'members': [st.session_state.current_user['id']]
    }
    st.session_state.groups.append(new_group)
    save_db(get_current_db_state())
    st.success(f"Group '{name}' created!")
    time.sleep(1)
    st.rerun()

def join_group(invite_code):
    # Reload DB to ensure we have the latest groups from other users
    fresh_db = load_db()
    st.session_state.groups = fresh_db.get('groups', [])
    
    code = invite_code.strip().upper()
    found_group = next((g for g in st.session_state.groups if g['invite_code'] == code), None)
    
    if found_group:
        if st.session_state.current_user['id'] not in found_group['members']:
            found_group['members'].append(st.session_state.current_user['id'])
            save_db({'users': fresh_db['users'], 'groups': st.session_state.groups, 'shared_items': fresh_db['shared_items']})
            st.success(f"Joined group '{found_group['name']}'!")
            time.sleep(1)
            st.rerun()
        else:
            st.info("You are already a member of this group.")
    else:
        st.error("Invalid invite code.")

def save_item(group_id, name, price, qty, sharable_qty, unit, photo, source, expiration_date):
    
    # Calculate initial claim (what the creator keeps)
    claims = {}
    if sharable_qty < qty:
        keep_qty = int(qty - sharable_qty)
        claims[st.session_state.current_user['id']] = keep_qty

    new_item = {
        'id': str(uuid.uuid4())[:8],
        'group_id': group_id,
        'created_by': st.session_state.current_user['id'],
        'created_at': datetime.now(),
        'name': name,
        'price': float(price),
        'total_qty': int(qty),
        'sharable_qty': int(sharable_qty),
        'unit': unit,
        'photo': photo, # Note: Photos won't persist well in JSON if they are bytes. Streamlit handles this in session but for JSON we skip bytes or need external storage.
        'source': source,
        'expiration_date': expiration_date,
        'claims': claims,
        'comments': []
    }
    # Clean photo for JSON storage (JSON cannot store file object)
    # in a real app, upload to S3/Cloudinary and store URL.
    # Here we just drop the photo object for persistence safety or keep if it's not bytes.
    # Streamlit UploadedFile is not JSON serializable.
    item_for_db = new_item.copy()
    item_for_db['photo'] = None # Removing photo from DB persistence for now to avoid crash
    
    st.session_state.shared_items.append(item_for_db)
    save_db(get_current_db_state())

def delete_item(item_id):
    st.session_state.shared_items = [i for i in st.session_state.shared_items if i['id'] != item_id]
    save_db(get_current_db_state())
    st.rerun()

def toggle_claim(item_id, delta):
    # Reload items to ensure concurrency safety
    fresh_db = load_db()
    st.session_state.shared_items = fresh_db.get('shared_items', [])
    
    for item in st.session_state.shared_items:
        if item['id'] == item_id:
            current_user_id = st.session_state.current_user['id']
            current_claim = item['claims'].get(current_user_id, 0)
            
            new_claim = max(0, current_claim + delta)
            
            # 1. Physical Total Check
            total_claimed_by_others = sum(q for uid, q in item['claims'].items() if uid != current_user_id)
            if total_claimed_by_others + new_claim > item['total_qty']:
                st.toast("Cannot claim more than total available!")
                st.rerun()
                return

            # 2. Sharable Limit Check (for non-creators)
            sharable_limit = item.get('sharable_qty', item['total_qty'])
            if current_user_id != item['created_by']:
                # Sum of claims by ALL non-creators (including current user's new claim)
                other_non_creators_claim = sum(q for uid, q in item['claims'].items() 
                                             if uid != current_user_id and uid != item['created_by'])
                
                if other_non_creators_claim + new_claim > sharable_limit:
                    st.toast(f"Limit reached! Only {sharable_limit} {item['unit']} are sharable.")
                    st.rerun()
                    return

            if new_claim == 0:
                 if current_user_id in item['claims']:
                     del item['claims'][current_user_id]
            else:
                 item['claims'][current_user_id] = new_claim
            
            save_db(get_current_db_state())
            st.rerun()

def add_comment(item_id, text):
    fresh_db = load_db()
    st.session_state.shared_items = fresh_db.get('shared_items', [])
    
    for item in st.session_state.shared_items:
        if item['id'] == item_id:
            if 'comments' not in item:
                item['comments'] = []
            item['comments'].append({
                'user_id': st.session_state.current_user['id'],
                'text': text,
                'timestamp': datetime.now()
            })
            save_db(get_current_db_state())
            st.rerun()

# --- 3. UI - Authentication ---
st.set_page_config(page_title="FreshSplit", page_icon="🍒", layout="centered")

# Capture invite code from URL if present
try:
    if "invite" in st.query_params:
        st.session_state.pending_invite = st.query_params["invite"]
except:
    pass # Fallback for older streamlit versions if needed

if not st.session_state.current_user:
    st.title("🍒 FreshSplit")
    st.write("Turn bulk shopping into shared savings.\nPost an item, friends claim their portion, and the app handles the split. Simple, fair, and stress-free.")
    
    name_input = st.text_input("Enter your name to start")
    if st.button("Start"):
        if name_input:
            login(name_input)
    st.stop()

# --- 4. UI - Main App ---
user = st.session_state.current_user

# Sidebar for Group Selection
st.sidebar.title(f"Hi, {user['name']}")
st.sidebar.header("Your Groups")

# Group Creation in Sidebar
with st.sidebar.expander("Create New Group"):
    new_group_name = st.text_input("Group Name")
    if st.button("Create"):
        if new_group_name:
            create_group(new_group_name)

# Group Join in Sidebar
with st.sidebar.expander("Join Group", expanded=bool(st.session_state.get('pending_invite'))):
    default_code = st.session_state.get('pending_invite', "")
    invite_code_input = st.text_input("Invite Code", value=default_code)
    if st.button("Join"):
        if invite_code_input:
            join_group(invite_code_input)
            # Clear pending invite after join attempt
            if 'pending_invite' in st.session_state:
                del st.session_state.pending_invite

# Group Selection
my_groups = [g for g in st.session_state.groups if user['id'] in g['members']]
selected_group = None

if my_groups:
    group_names = [g['name'] for g in my_groups]
    selected_group_name = st.sidebar.radio("Select Group", group_names)
    selected_group = next((g for g in my_groups if g['name'] == selected_group_name), None)
else:
    st.info("👈 Create a group in the sidebar to get started.")

# --- 5. Group Detail View ---
if selected_group:
    st.title(selected_group['name'])
    
    st.info(f"👫 Invite friends to this group by sharing this link:")
    st.code(f"http://localhost:8501/?invite={selected_group['invite_code']}", language="text")
    
    # --- Balance Summary ---
    summary_items = [i for i in st.session_state.shared_items if i['group_id'] == selected_group['id']]
    owed_to_me = {} # {user_id: amount}
    i_owe = {}      # {user_id: amount}

    for item in summary_items:
        if item['total_qty'] == 0: continue
        unit_price = item['price'] / item['total_qty']
        poster_id = item['created_by']
        
        for claimer_id, qty in item['claims'].items():
            if claimer_id == poster_id: continue # Creator keeping their own item is not a debt
            
            cost = qty * unit_price
            
            # If I am the poster, this person owes me
            if poster_id == user['id']:
                owed_to_me[claimer_id] = owed_to_me.get(claimer_id, 0) + cost
            
            # If I am the claimer, I owe the poster
            if claimer_id == user['id']:
                i_owe[poster_id] = i_owe.get(poster_id, 0) + cost

    if owed_to_me or i_owe:
        sc1, sc2 = st.columns(2)
        with sc1:
            if i_owe:
                st.write("💸 **You Owe**")
                for uid, amount in i_owe.items():
                    u_name = st.session_state.users.get(uid, "Unknown")
                    st.write(f"- {u_name}: ${amount:.2f}")
        with sc2:
            if owed_to_me:
                st.write("💰 **Owed to You**")
                for uid, amount in owed_to_me.items():
                    u_name = st.session_state.users.get(uid, "Unknown")
                    st.write(f"- {u_name}: ${amount:.2f}")
        st.divider()
    
    # Add Item Form (Batch Mode)
    with st.expander("➕ Add Items"):
        with st.form("add_item_form", clear_on_submit=True):
            st.caption("Add multiple items to a batch, then post them all at once.")
            # Row 1
            c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
            i_name = c1.text_input("Item Name", placeholder="Toilet Paper")
            i_price = c2.number_input("Total Price ($)", min_value=0.0, step=0.01)
            i_qty = c3.number_input("Total Qty", min_value=1, step=1, value=1)
            # Note: Sharable defaults to full qty if not specified, logic handles clamping
            i_sharable = c4.number_input("Sharable Qty", min_value=0, step=1, value=1) 
            i_unit = c5.text_input("Unit", value="pcs")
            
            # Row 2
            r2_c1, r2_c2, r2_c3 = st.columns([3, 3, 4])
            i_source = r2_c1.text_input("Source", placeholder="e.g. Costco")
            i_expiration = r2_c2.date_input("Expiration Date", value=None)
            i_photo = r2_c3.file_uploader("Item Photo", type=['png', 'jpg', 'jpeg'])
            
            submitted = st.form_submit_button("Add to Batch")
            if submitted:
                if i_name and i_price > 0:
                    # Logic to clamp sharable qty
                    final_sharable = min(i_sharable, i_qty) if i_sharable > 0 else i_qty

                    st.session_state.draft_items.append({
                        'name': i_name,
                        'price': i_price,
                        'qty': i_qty,
                        'sharable_qty': final_sharable,
                        'unit': i_unit,
                        'photo': i_photo,
                        'source': i_source,
                        'expiration_date': i_expiration
                    })
                    st.success(f"Added '{i_name}' to batch!")
        
        # Display Batch
        if st.session_state.draft_items:
            st.divider()
            st.write(f"**Batch ({len(st.session_state.draft_items)} items)**")
            for idx, d in enumerate(st.session_state.draft_items):
                st.text(f"{idx+1}. {d['name']} (${d['price']})")
            
            if st.button("🚀 Post All Items"):
                for d in st.session_state.draft_items:
                    save_item(selected_group['id'], **d)
                st.session_state.draft_items = []
                st.rerun()

    st.divider()

    # List Items
    group_items = [i for i in st.session_state.shared_items if i['group_id'] == selected_group['id']]
    
    if not group_items:
        st.info("No items yet.")
    
    for item in group_items:
        # Calculations
        claimed_qty = sum(item['claims'].values())
        remaining = item['total_qty'] - claimed_qty
        unit_price = item['price'] / item['total_qty'] if item['total_qty'] > 0 else 0
        my_claim = item['claims'].get(user['id'], 0)
        my_cost = my_claim * unit_price
        
        # Card UI
        with st.container():
            c1, c2 = st.columns([3, 2])
            
            with c1:
                if item.get('photo'):
                    st.image(item['photo'], use_column_width=True)
                st.subheader(item['name'])
                st.write(f"**${item['price']:.2f}** total • ${unit_price:.2f}/{item['unit']}")
                
                details = []
                if item.get('source'):
                    details.append(f"🏪 {item['source']}")
                if item.get('expiration_date'):
                    details.append(f"⏳ Exp: {item['expiration_date']}")
                
                if details:
                    st.caption(" • ".join(details))
                
                if remaining < 0:
                    st.error(f"{remaining} left (Overclaimed!)")
                elif remaining == 0:
                    st.success("Fully Claimed ✅")
                else:
                    st.progress(claimed_qty / item['total_qty'])
                    st.caption(f"{remaining} {item['unit']} remaining")
                
                # Show who claimed what
                if item['claims']:
                    st.write("**Claims:**")
                    for claim_uid, claim_qty in item['claims'].items():
                        claim_user_name = st.session_state.users.get(claim_uid, "Unknown")
                        st.text(f"- {claim_user_name}: {claim_qty} {item['unit']}")

            with c2:
                st.write(f"**You want: {my_claim}**")
                b1, b2 = st.columns(2)
                if b1.button("➖", key=f"d_{item['id']}"):
                    toggle_claim(item['id'], -1)
                if b2.button("➕", key=f"u_{item['id']}"):
                    toggle_claim(item['id'], 1)
                
                if my_cost > 0:
                    st.info(f"Owe: ${my_cost:.2f}")

                # Delete Button (Only for Creator)
                if item['created_by'] == user['id']:
                    if st.button("🗑️ Delete", key=f"del_{item['id']}"):
                        delete_item(item['id'])

            # Comments Section
            with st.expander(f"💬 Comments ({len(item.get('comments', []))})"):
                for c in item.get('comments', []):
                    c_user = st.session_state.users.get(c['user_id'], "Unknown")
                    st.caption(f"**{c_user}:** {c['text']}")
                
                with st.form(key=f"comment_form_{item['id']}", clear_on_submit=True):
                    new_comment = st.text_input("Write a comment...")
                    if st.form_submit_button("Post"):
                        if new_comment:
                            add_comment(item['id'], new_comment)

            st.divider()
