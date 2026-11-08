Feature: Score history
  The chart and its table show how many accusations each person has had ratified in each academic year.

  Scenario: A chart and a table of the yearly totals
    Given I am signed in as a member
    And "Alice" has 2 ratified accusations from 2023
    And "Alice" has 1 ratified accusations from 2024
    And "Bob" has 1 ratified accusations from 2024
    When I open "/ferries/score-history/"
    Then the score table should have the years "2023/24, 2024/25"
    And the score table should show "Alice" with 2, 1
    And the score table should show "Bob" with 0, 1
    And the chart should have 2 lines
    And there should be no JavaScript errors

  Scenario: Nothing to show yet
    Given I am signed in as a member
    When I open "/ferries/score-history/"
    Then I should see "No score history available."
    And there should be no JavaScript errors
