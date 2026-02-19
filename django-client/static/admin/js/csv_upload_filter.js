document.addEventListener("DOMContentLoaded", function () {
    var recordTypeSelect = document.getElementById("id_record_type");
    var profileSelect = document.getElementById("id_format_profile");
    if (!recordTypeSelect || !profileSelect) return;

    var mapEl = document.getElementById("profile-record-type-map");
    if (!mapEl) return;
    var profileMap = JSON.parse(mapEl.textContent);

    var allOptions = Array.prototype.slice.call(profileSelect.options);

    function filterProfiles() {
        var selectedType = recordTypeSelect.value;
        var currentValue = profileSelect.value;
        profileSelect.innerHTML = "";

        allOptions.forEach(function (opt) {
            if (!opt.value) {
                profileSelect.appendChild(opt.cloneNode(true));
                return;
            }
            var optRecordType = profileMap[opt.value];
            if (!selectedType || optRecordType === selectedType) {
                profileSelect.appendChild(opt.cloneNode(true));
            }
        });

        var found = false;
        for (var i = 0; i < profileSelect.options.length; i++) {
            if (profileSelect.options[i].value === currentValue) {
                found = true;
                break;
            }
        }
        if (!found) {
            profileSelect.value = "";
        } else {
            profileSelect.value = currentValue;
        }
    }

    recordTypeSelect.addEventListener("change", filterProfiles);
    filterProfiles();
});
