// Active navigation links
const navLinkElements = document.querySelectorAll('.nav-link');
const windowPathname = window.location.pathname;

navLinkElements.forEach(navLink =>{
    var navLinkPathname = new URL(navLink.href).pathname;
    navLinkPathname = navLinkPathname.substring(navLinkPathname.indexOf('/') + 1);

    if (windowPathname.includes(navLinkPathname)) {
        navLink.classList.add('active');
    }
});