function form_element()
{
    let aspirant = document.getElementById("aspirant");
    let employer = document.getElementById("employer");

    let field = document.getElementById("org");

    if(employer.checked==true)
    {
        field.setAttribute("placeholder", "Company");
    }
    if(aspirant.checked==true)
    {
        field.setAttribute("placeholder", "Institute");
    }
}

