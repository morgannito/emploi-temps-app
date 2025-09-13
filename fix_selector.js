    function changeWeekPlanningV2(selectedOption) {
        var select = document.getElementById('week-select');
        var selectedText = select.options[select.selectedIndex].text;
        var weekMatch = selectedText.match(/Semaine \d+ [AB]/);
        if (weekMatch) {
            var weekName = encodeURIComponent(weekMatch[0]);
            window.location.href = '/planning_v2/' + weekName;
        }
    }
