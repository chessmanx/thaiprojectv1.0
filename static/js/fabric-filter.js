document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("searchInput");
  const regionFilter = document.getElementById("regionFilter");
  const cards = document.querySelectorAll(".fabric-card");

  function filterCards() {
    const searchText = searchInput.value.toLowerCase();
    const selectedRegion = regionFilter.value;

    cards.forEach(card => {
      const name = card.getAttribute("data-name").toLowerCase();
      const region = card.getAttribute("data-region");

      const matchesSearch = name.includes(searchText);
      const matchesRegion = selectedRegion === "all" || region === selectedRegion;

      card.style.display = (matchesSearch && matchesRegion) ? "block" : "none";
    });
  }

  searchInput.addEventListener("input", filterCards);
  regionFilter.addEventListener("change", filterCards);
});
