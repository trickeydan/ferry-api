Feature: Light and dark themes
  The theme follows the system by default, and a choice is remembered.

  Scenario: Following the system theme
    Given I am signed in as a member
    And my system is set to a dark theme
    When I open "/"
    Then the page should use the dark theme

  Scenario: A chosen theme is remembered
    Given I am signed in as a member
    And my system is set to a light theme
    When I open "/"
    Then the page should use the light theme
    When I choose the "Dark" theme
    Then the page should use the dark theme
    When I reload the page
    Then the page should use the dark theme
    When I open "/pub/"
    Then the page should use the dark theme
    When I choose the "Light" theme
    And I reload the page
    Then the page should use the light theme
    And there should be no JavaScript errors

  Scenario: Auto follows the system as it changes
    Given I am signed in as a member
    And my system is set to a light theme
    When I open "/"
    And I choose the "Auto" theme
    Then the page should use the light theme
    When my system changes to a dark theme
    Then the page should use the dark theme
    And there should be no JavaScript errors
