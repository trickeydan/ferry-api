Feature: Using the site on a phone

  Scenario: The menu collapses behind a button
    Given I am signed in as a member
    And I am using a phone
    When I open "/"
    Then the menu should be collapsed
    When I open the menu
    And I click the "Ferries" link
    Then I should be on "/ferries/"

  Scenario Outline: Pages fit the screen
    Given I am signed in as a member
    And the app has plenty of data
    And the next pub is at "The Anchor and Hope Public House"
    And I am using a phone with large text
    When I open "<path>"
    Then the page should not scroll sideways

    Examples:
      | path                   |
      | /                      |
      | /ferries/              |
      | /ferries/scoreboard/   |
      | /ferries/accusations/  |
      | /ferries/consequences/ |
      | /pub/                  |
      | /pub/events            |
      | /pub/pubs/             |
      | /accounts/people/      |
      | /accounts/profile/     |
      | /accounts/profile/api-tokens/ |
