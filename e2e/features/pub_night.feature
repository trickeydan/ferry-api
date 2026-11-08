Feature: A pub night from start to finish
  An admin schedules a pub night, members respond, and once it has happened it counts towards the stats and streaks.

  Scenario: Scheduling, skipping, and the afterwards
    Given I am signed in as a member using AutoPub
    And "Bob" is a member using AutoPub
    And "Carol" is a member not using AutoPub
    When an admin schedules a pub night at "The Anchor" for next week
    And I open "/"
    Then I should see "The Anchor"
    And I should see "2 attending"
    And I should see "You're going"

    When I click the "Skip next pub" button
    Then I should see "You skipped this one"
    And I should see "1 attending"
    When I click the "Undo skip" button
    Then I should see "You're going"
    And I should see "2 attending"

    When I open the next pub's page
    Then I should see "Attendees (2)"
    And I should see "Bob"

    When the pub night has happened
    And I open "/"
    Then the pub stats should show 1 event with an average of 2.0 attendees
    When I open "/accounts/people/"
    Then "Bob" should have a pub streak of 1
    And "Test Member" should have a pub streak of 1
    And "Carol" should have a pub streak of 0
