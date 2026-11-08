Feature: Deactivating consequences and API tokens
  Deactivating asks for confirmation first, then updates the row in place.

  Scenario: Deactivating a consequence
    Given I am signed in as a member
    And I have a consequence "Buy the next round"
    When I open "/ferries/consequences/"
    Then the consequence "Buy the next round" should be enabled
    When I click the "Deactivate" button
    And I confirm the dialog
    Then the consequence "Buy the next round" should be disabled

  Scenario: Dismissing the confirmation keeps the consequence
    Given I am signed in as a member
    And I have a consequence "Buy the next round"
    When I open "/ferries/consequences/"
    And I click the "Deactivate" button
    And I dismiss the dialog
    Then the dialog should be closed
    And the consequence "Buy the next round" should be enabled

  Scenario: Deactivating and reactivating an API token
    Given I am signed in as a member
    And I have an API token called "Discord bot"
    When I open "/accounts/profile/api-tokens/"
    Then the API token "Discord bot" should be active
    When I click the "Deactivate" button
    And I confirm the dialog
    Then the API token "Discord bot" should be inactive
    When I click the "Reactivate" button
    And I confirm the dialog
    Then the API token "Discord bot" should be active
