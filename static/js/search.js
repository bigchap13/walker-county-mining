const box=document.getElementById("globalSearch");
const list=document.getElementById("searchResults");

async function runSearch(){

    const q=box.value.trim();

    if(!q){
        list.innerHTML="";
        return;
    }

    const data=await fetch("/api/search?q="+encodeURIComponent(q)).then(r=>r.json());

    list.innerHTML=data.map(r=>`
<a class="map-record mine-row" href="${r.url}">
<strong>${r.title}</strong>
<small>${r.type} • ${r.subtitle}</small>
</a>
`).join("");
}

box.addEventListener("input",runSearch);
