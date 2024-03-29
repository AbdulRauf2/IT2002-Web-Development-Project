from django.urls import reverse
from readline import insert_text
from django.shortcuts import render, redirect
from django.db import connection

from app.helper import queries


def index(request):
    """Shows the main page"""
    return render(request, 'app/index.html')


def login(request):
    """Shows the user login page"""
    context = {}
    status = ''

    if request.POST:
        email = request.POST['login_email']
        pw = request.POST['login_password']
        auth = queries.authenticate_user(email, pw)
        if auth:
            context['user_page'] = 'Me'
            return redirect(reverse('user_index', kwargs={'email':email}))
        else:
            status = "Wrong email or password. Please try again."
            context['status'] = status

    return render(request, "app/login.html", context)



def register(request):
    """Shows the user registration page"""
    context = {}
    status = ''

    if request.POST:
        status = queries.insert_user(request.POST)

    context['status'] = status
    if status == 'Successfully registered.':
        context['redirect_msg'] = 'You may now login to our App.'
 
    return render(request, "app/user-registration.html", context)


def user_index(request, email):
    """Shows user's homepage after login"""
    # return render(request, 'app/index.html')
    return index(request)


def search(request):
    """Shows user's homepage after login"""
    result_dict = {}
    if request.POST:
        if request.POST['action'] == 'search':
            with connection.cursor() as cursor:
                cursor.execute(
                    # uses user-defined SQL function
                    "SELECT * FROM get_apartment(%s,%s,%s)",
                    [
                        request.POST['country'],
                        request.POST['city'],
                        request.POST['num_guests']
                    ]
                )                
                apartments = queries.dictfetchall_(cursor)
            result_dict['records'] = apartments
            result_dict['orderby'] = 'price'

            return render(request,'app/search-apartments.html', result_dict)
    
    else:
        # default results with all apartments
        # ordered by price asc
        with connection.cursor() as cursor:
            cursor.execute(
                # uses user-defined SQL function
                "SELECT * FROM get_all_apartments()"
            )
            apartments = queries.dictfetchall_(cursor)
        result_dict['records'] = apartments
        result_dict['orderby'] = 'price'
    
    if request.GET:
        if request.GET['orderby'] == 'price':
            result_dict['orderby'] = 'price'
        elif request.GET['orderby'] == 'rating':
            result_dict['orderby'] = 'avg_rating'

    return render(request,'app/search-apartments.html', result_dict)


def user_search(request, email):
    return search(request)


def apartment(request, apt_id):
    """Shows the apartment details page"""
    
    result_dict = dict()

    result_dict['apt'] = queries.get_single_apartment(apt_id)

    if request.POST:
        if request.POST.get('action') == 'checkavail':
            dates_avail = queries.find_apt_availability(request.POST, apt_id)
            result_dict['dates_avail'] = dates_avail
        elif request.POST.get('action') == 'book':
            status = queries.user_make_booking(request.POST, apt_id)
            result_dict['status'] = status
            

    return render(request,'app/apartment.html', result_dict)


def user_view_apt(request, email, apt_id):
    """Shows the apartment details page for login user"""
    return apartment(request, apt_id)


def viewself(request, email):
    """
    Shows the view user details page after login, 
    which include user details and rental data
    """
    context = {}
    
    if request.POST:
        if request.POST['action'] == 'rate':
            status = queries.user_update_rental_rating(
                request.POST['rental_id'],
                request.POST['rating'],
            )
            context['rate_status'] = status
        elif request.POST['action'] == 'delete_booking':
            status = queries.user_delete_booking(request.POST['tempbooking_id'])
            context['delete_booking_status'] = status

    # call method form helper module queries
    context['user'] = queries.get_single_user(email)
    context['bookings'] = queries.get_user_bookings(email)
    context['rentals'] = queries.get_user_rentals(email)

    return render(request,'app/viewself-guest.html', context)



def viewself_host(request, email):
    """
    Shows the view user details page after login, 
    which include user details and rental data
    """
    context = {}
    if request.POST:
        if request.POST['action'] == 'approve':
            status = queries.host_approve_booking(request.POST['tempbooking_id'])
            context['status'] = status

        elif request.POST['action'] == 'delete':
            status = queries.host_delete_booking(request.POST['tempbooking_id'])
            context['status'] = status
        
        elif request.POST['action'] == 'edit-apt':
            return redirect(reverse('edit-apt', kwargs={
                'email':email, 'apt_id':request.POST['apartment_id']
            }))
        elif request.POST['action'] == 'unlist-apt':
            status = queries.host_toggle_apt_listing(request.POST['apartment_id'])
            context['status'] = status

    context['apartments'] = queries.get_host_apartments(email)
    context['bookings'] = queries.get_host_bookings(email)
    context['upcoming_rentals'] = queries.host_upcoming_rentals(email)
    context['past_rentals'] = queries.host_past_rentals(email)

    return render(request,'app/viewself-host.html', context)

def new_apt(request, email):
    context = {}
    context['email'] = email
    context['operation'] = 'Add'
    if request.POST:
        if request.POST['action'] == 'newapt':
            status = queries.host_new_apt(request.POST, email)
            context['status'] = status
    return render(request, 'app/new-apartment.html', context)

def edit_apt(request, email, apt_id):
    context = {}
    context['email'] = email
    context['operation'] = 'Update'
    apartment = queries.get_single_apartment(apt_id)
    context['apartment'] = apartment

    # check radio buttons according to info from database query
    property_types = {
        "Luxury Apartment": 't1',
        "Bungalow": 't2',
        "Apartment": 't3',
    }
    context = radio_helper(context, property_types, apartment['property_type'])
    amenities = {
        "Free Wifi/Washing Machine and Dryer": 'am1',
        "Free Wifi/Parking/Gym/Pool/Washing Machine and Dryer": 'am2',
        "Free Wifi/Parking/Washing Machine and Dryer": 'am3',
    }
    context = radio_helper(context, amenities, apartment['amenities'])
    house_rules = {
        "No Pets": 'hr1',
        "No Smoking": 'hr2',
        "No Smoking/No Pets": 'hr3',
    }
    context = radio_helper(context, house_rules, apartment['house_rules'])

    if request.POST:
        if request.POST['action'] == 'newapt':
            status = queries.host_edit_apt(request.POST, apt_id)
            context['status'] = status
    return render(request, 'app/new-apartment.html', context)



def checkpw(request, email):
    """Shows page to enter password and allow user to edit own details once password matches"""
    result_dict = {}
    status = ''

    if request.POST:
        if request.POST['action'] == 'enterpw':
            # auth is True is password submitted matches DB record
            auth = queries.authenticate_user(email, request.POST['password'])
            if auth:
                user = queries.get_single_user(email)
                result_dict['user'] = user
                card_types = {
                    'visa': 'visa',
                    'americanexpress': 'americanexpress',
                    'mastercard': 'mastercard',
                }
                result_dict = radio_helper(result_dict, card_types, user['credit_card_type'])
                return render(request, "app/edit.html", result_dict)
            else:
                status = 'Incorrect password!'
                result_dict = {'status': status}
                return render(request, "app/checkpw.html", result_dict)


        elif request.POST['action'] == 'Update':
            status = queries.update_user(request.POST, email)
            result_dict['status'] = status

            user = queries.get_single_user(email)
            result_dict['user'] = user
            card_types = {
                    'visa': 'visa',
                    'americanexpress': 'americanexpress',
                    'mastercard': 'mastercard',
                }
            result_dict = radio_helper(result_dict, card_types, user['credit_card_type'])

            return render(request, "app/edit.html", result_dict)

    result_dict["status"] = status
    result_dict["email"] = email
    return render(request, "app/checkpw.html", result_dict)



def radio_helper(context:dict, types:dict, val:str):
    """
    Helper function to ensure radio buttons are checked accordingly
    Use in views where user edits his details
    """
    assert len(types) == 3
    for k, v in types.items():
        context[k] = ''
    for k, v in types.items():
        if k == val:
            context[v] = "checked" # check radio button
    return context