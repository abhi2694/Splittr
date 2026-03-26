from flask import Blueprint, request, jsonify, session
from models import db, User, Group, GroupMember, Expense, ExpenseSplit, Wallet, WalletTransaction
from datetime import datetime

groups = Blueprint("groups", __name__)

@groups.route("/create-group", methods=["POST"])
def create_group():
    user_id = session.get("user_id")
    data = request.json

    name = data.get("name")
    members = data.get("members", [])

    if not name:
        return jsonify({"error": "Group name required"}), 400

    group = Group(name=name, created_by=user_id)
    db.session.add(group)
    db.session.commit()

    # Add creator
    db.session.add(GroupMember(group_id=group.id, user_id=user_id))

    # Add other members
    for email in members:
        user = User.query.filter_by(email=email).first()
        if user:
            db.session.add(GroupMember(group_id=group.id, user_id=user.id))

    db.session.commit()

    return jsonify({"message": "Group created", "group_id": group.id})

@groups.route("/my-groups")
def my_groups():
    user_id = session.get("user_id")

    memberships = GroupMember.query.filter_by(user_id=user_id).all()

    group_ids = [m.group_id for m in memberships]

    groups = Group.query.filter(Group.id.in_(group_ids)).all()

    result = [{"id": g.id, "name": g.name} for g in groups]

    return jsonify(result)

@groups.route("/add-expense", methods=["POST"])
def add_expense():
    user_id = session.get("user_id")
    data = request.json

    group_id = data.get("group_id")
    amount = float(data.get("amount"))
    description = data.get("description")
    splits = data.get("splits")  # [{user_id, amount}]
    category = data.get("category", "General")

    # Create expense
    expense = Expense(
        group_id=group_id,
        paid_by=user_id,
        amount=amount,
        description=description,
        category=category
    )

    db.session.add(expense)
    db.session.commit()

    # Add splits
    for split in splits:
        db.session.add(ExpenseSplit(
            expense_id=expense.id,
            user_id=split["user_id"],
            amount=split["amount"]
        ))

    # 💰 WALLET LOGIC (NEW)
    wallet = Wallet.query.filter_by(user_id=user_id).first()

    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0)
        db.session.add(wallet)

    wallet.balance -= amount

    db.session.add(WalletTransaction(
        user_id=user_id,
        amount=-amount,
        type="expense",
        description=description or "Group expense"
    ))

    db.session.commit()

    return jsonify({"message": "Expense added"})

@groups.route("/group-balances/<int:group_id>")
def group_balances(group_id):
    expenses = Expense.query.filter_by(group_id=group_id).all()

    balances = {}

    for exp in expenses:
        payer = exp.paid_by
        if payer not in balances:
            balances[payer] = 0
        balances[payer] += exp.amount

        splits = ExpenseSplit.query.filter_by(expense_id=exp.id).all()

        for s in splits:
            if s.user_id not in balances:
                balances[s.user_id] = 0
            balances[s.user_id] -= s.amount

    return jsonify(balances)

@groups.route("/group-members/<int:group_id>")
def group_members(group_id):
    members = GroupMember.query.filter_by(group_id=group_id).all()

    users = []
    for m in members:
        user = User.query.get(m.user_id)

        # ✅ Skip broken entries
        if not user:
            continue

        users.append({
            "id": user.id,
            "name": user.name,
            "email": user.email
        })

    return jsonify(users)

@groups.route("/add-member", methods=["POST"])
def add_member():
    data = request.json

    group_id = data.get("group_id")
    email = data.get("email")

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "User not found"}), 404

    # prevent duplicates
    existing = GroupMember.query.filter_by(
        group_id=group_id,
        user_id=user.id
    ).first()

    if existing:
        return jsonify({"error": "Already in group"}), 400

    db.session.add(GroupMember(group_id=group_id, user_id=user.id))
    db.session.commit()

    return jsonify({"message": "Member added"})

@groups.route("/group-expenses/<int:group_id>")
def group_expenses(group_id):
    expenses = Expense.query.filter_by(group_id=group_id)\
        .order_by(Expense.created_at.desc()).all()

    result = []

    for e in expenses:
        payer = User.query.get(e.paid_by)

        splits = ExpenseSplit.query.filter_by(expense_id=e.id).all()
        split_data = []

        for s in splits:
            user = User.query.get(s.user_id)
            split_data.append({
                "name": user.name,
                "amount": s.amount
            })

        result.append({
            "id": e.id,
            "amount": e.amount,
            "description": e.description,
            "paid_by": payer.name,
            "created_at": e.created_at.strftime("%d %b %Y"),
            "splits": split_data
        })

    return jsonify(result)

@groups.route("/overall-balances")
def overall_balances():
    user_id = session.get("user_id")

    memberships = GroupMember.query.filter_by(user_id=user_id).all()
    group_ids = [m.group_id for m in memberships]

    balances = {}

    for gid in group_ids:
        expenses = Expense.query.filter_by(group_id=gid).all()

        for exp in expenses:
            payer = exp.paid_by

            if payer not in balances:
                balances[payer] = 0
            balances[payer] += exp.amount

            splits = ExpenseSplit.query.filter_by(expense_id=exp.id).all()

            for s in splits:
                if s.user_id not in balances:
                    balances[s.user_id] = 0
                balances[s.user_id] -= s.amount

    # Remove current user from map
    balances.pop(user_id, None)

    # Attach names
    result = []
    for uid, val in balances.items():
        user = User.query.get(uid)
        result.append({
            "name": user.name,
            "amount": val
        })

    return jsonify(result)

@groups.route("/wallet")
def get_wallet():
    user_id = session.get("user_id")

    wallet = Wallet.query.filter_by(user_id=user_id).first()

    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0)
        db.session.add(wallet)
        db.session.commit()

    return jsonify({"balance": wallet.balance})

@groups.route("/add-money", methods=["POST"])
def add_money():
    user_id = session.get("user_id")
    data = request.json

    amount = float(data.get("amount"))

    wallet = Wallet.query.filter_by(user_id=user_id).first()

    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0)
        db.session.add(wallet)

    wallet.balance += amount

    db.session.add(WalletTransaction(
        user_id=user_id,
        amount=amount,
        type="add_money",
        description="Added money"
    ))

    db.session.commit()

    return jsonify({"message": "Money added"})

@groups.route("/transactions")
def get_transactions():
    user_id = session.get("user_id")

    txns = WalletTransaction.query\
        .filter_by(user_id=user_id)\
        .order_by(WalletTransaction.created_at.desc())\
        .all()

    result = []
    for t in txns:
        result.append({
            "amount": t.amount,
            "type": t.type,
            "description": t.description,
            "date": t.created_at.strftime("%d %b")
        })

    return jsonify(result)

@groups.route("/monthly-summary")
def monthly_summary():
    user_id = session.get("user_id")

    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)

    expenses = Expense.query.filter(
        Expense.created_at >= month_start
    ).all()

    total = 0
    category_map = {}

    for e in expenses:
        if e.paid_by == user_id:
            total += e.amount

            category = e.category or "General"

            if category not in category_map:
                category_map[category] = 0

            category_map[category] += e.amount
    budget = session.get("budget", 0)
    
    return jsonify({
        "total": total,
        "categories": category_map,
        "budget": budget
    })

@groups.route("/set-budget", methods=["POST"])
def set_budget():
    session["budget"] = request.json.get("amount")
    return jsonify({"message": "Budget set"})